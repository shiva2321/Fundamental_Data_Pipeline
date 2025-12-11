"""
Batch Profile Processor - Process multiple companies in parallel

Features:
- Concurrent processing of multiple tickers
- Progress tracking per ticker
- Non-blocking UI updates
- Graceful error handling
- Resume capability
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from queue import Queue
import time

logger = logging.getLogger("batch_profile_processor")


class BatchProfileProcessor:
    """
    Process multiple company profiles in parallel with progress tracking.
    """

    def __init__(self, mongo, parallel_aggregator, max_concurrent_companies=3):
        """
        Initialize batch processor.
        
        Args:
            mongo: MongoDB wrapper
            parallel_aggregator: ParallelProfileAggregator instance
            max_concurrent_companies: Number of companies to process simultaneously
        """
        self.mongo = mongo
        self.aggregator = parallel_aggregator
        self.max_concurrent = max_concurrent_companies
        
        # Progress tracking
        self.progress_queue = Queue()
        self.results = {}
        self.errors = {}
        self.lock = threading.Lock()
        
    def process_batch(
        self,
        companies: List[Dict[str, str]],  # List of {'cik': ..., 'ticker': ..., 'name': ...}
        options: Optional[Dict] = None,
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process multiple companies in parallel.
        
        Args:
            companies: List of company dicts with cik, ticker, name
            options: Processing options (lookback_years, etc.)
            progress_callback: Called with (ticker, status, message)
            completion_callback: Called when batch is complete
            
        Returns:
            Dict with results and statistics
        """
        opts = options or {}
        total = len(companies)
        
        logger.info(f"🚀 Starting batch processing of {total} companies")
        logger.info(f"   Concurrent companies: {self.max_concurrent}")
        logger.info(f"   Threads per company: {self.aggregator.max_workers}")
        
        start_time = time.time()
        
        # Initialize tracking
        self.results = {}
        self.errors = {}
        completed = 0
        
        # Process companies in parallel
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Create progress callback for each company
            def company_progress_callback(ticker):
                def callback(level, message):
                    if progress_callback:
                        progress_callback(ticker, level, message)
                return callback
            
            # Submit all company processing tasks
            future_to_company = {}
            
            for company in companies:
                cik = company['cik']
                ticker = company.get('ticker', cik)
                
                # Create individual progress callback
                cb = company_progress_callback(ticker)
                
                future = executor.submit(
                    self._process_single_company,
                    company,
                    opts,
                    cb
                )
                
                future_to_company[future] = company
            
            # Collect results as they complete
            for future in as_completed(future_to_company):
                company = future_to_company[future]
                ticker = company.get('ticker', company['cik'])
                
                try:
                    result = future.result(timeout=600)  # 10 minute timeout
                    
                    with self.lock:
                        self.results[ticker] = result
                        completed += 1
                    
                    logger.info(f"✅ Completed {ticker} ({completed}/{total})")
                    
                    if progress_callback:
                        progress_callback(ticker, 'complete', f"✅ Profile complete")
                        progress_callback(None, 'batch', f"Progress: {completed}/{total} companies")
                    
                except Exception as e:
                    with self.lock:
                        self.errors[ticker] = str(e)
                        completed += 1
                    
                    logger.error(f"❌ Failed {ticker}: {e}")
                    
                    if progress_callback:
                        progress_callback(ticker, 'error', f"❌ Error: {str(e)[:50]}")
        
        # Summary
        elapsed = time.time() - start_time
        success_count = len(self.results)
        error_count = len(self.errors)
        
        summary = {
            'total': total,
            'successful': success_count,
            'failed': error_count,
            'elapsed_seconds': elapsed,
            'avg_time_per_company': elapsed / max(total, 1),
            'results': self.results,
            'errors': self.errors
        }
        
        logger.info(f"✅ Batch complete: {success_count} successful, {error_count} failed in {elapsed:.1f}s")
        
        if completion_callback:
            completion_callback(summary)
        
        return summary

    def _process_single_company(
        self,
        company: Dict[str, str],
        options: Dict,
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """Process a single company (runs in separate thread)"""
        cik = company['cik']
        ticker = company.get('ticker', cik)
        
        try:
            progress_callback('info', f"🔄 Starting {ticker}...")
            
            # Use parallel aggregator
            profile = self.aggregator.aggregate_profile_parallel(
                cik=cik,
                company_info=company,
                output_collection='Fundamental_Data_Pipeline',
                options=options,
                progress_callback=progress_callback
            )
            
            if profile:
                progress_callback('info', f"✓ {ticker} aggregation complete")
                return profile
            else:
                raise Exception(f"No profile generated for {ticker}")
                
        except Exception as e:
            logger.exception(f"Error processing {ticker}")
            raise


class NonBlockingQueueProcessor:
    """
    Queue-based processor that runs completely in background.
    
    UI can add tasks to queue and receive progress updates without blocking.
    """

    def __init__(self, mongo, max_concurrent=3, threads_per_company=8):
        """Initialize non-blocking processor"""
        from src.analysis.parallel_profile_aggregator import ParallelProfileAggregator
        
        self.mongo = mongo
        self.max_concurrent = max_concurrent
        
        # Create parallel aggregator
        self.parallel_aggregator = ParallelProfileAggregator(
            mongo=mongo,
            max_workers=threads_per_company
        )
        
        # Create batch processor
        self.batch_processor = BatchProfileProcessor(
            mongo=mongo,
            parallel_aggregator=self.parallel_aggregator,
            max_concurrent_companies=max_concurrent
        )
        
        # Queue for tasks
        self.task_queue = Queue()
        self.is_processing = False
        self.processing_thread = None
        
        # Callbacks
        self.progress_callbacks = []
        self.completion_callbacks = []
        
    def add_task(self, companies: List[Dict], options: Optional[Dict] = None):
        """
        Add companies to processing queue (non-blocking).
        
        Args:
            companies: List of company dicts
            options: Processing options
        """
        task = {
            'companies': companies,
            'options': options or {},
            'added_at': time.time()
        }
        
        self.task_queue.put(task)
        logger.info(f"Added {len(companies)} companies to queue")
        
        # Start processor if not running
        if not self.is_processing:
            self.start_processing()
    
    def start_processing(self):
        """Start background processing thread"""
        if self.is_processing:
            logger.warning("Processor already running")
            return
        
        self.is_processing = True
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        logger.info("🚀 Background processor started")
    
    def stop_processing(self):
        """Stop background processing"""
        self.is_processing = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("⏹ Background processor stopped")
    
    def register_progress_callback(self, callback: Callable):
        """Register callback for progress updates"""
        self.progress_callbacks.append(callback)
    
    def register_completion_callback(self, callback: Callable):
        """Register callback for batch completion"""
        self.completion_callbacks.append(callback)
    
    def _processing_loop(self):
        """Main processing loop (runs in background thread)"""
        logger.info("Processing loop started")
        
        while self.is_processing:
            try:
                # Get next task (blocking with timeout)
                task = self.task_queue.get(timeout=1.0)
                
                companies = task['companies']
                options = task['options']
                
                logger.info(f"Processing batch of {len(companies)} companies")
                
                # Process batch
                def progress_cb(ticker, level, message):
                    for cb in self.progress_callbacks:
                        try:
                            cb(ticker, level, message)
                        except Exception as e:
                            logger.error(f"Progress callback error: {e}")
                
                def completion_cb(summary):
                    for cb in self.completion_callbacks:
                        try:
                            cb(summary)
                        except Exception as e:
                            logger.error(f"Completion callback error: {e}")
                
                self.batch_processor.process_batch(
                    companies=companies,
                    options=options,
                    progress_callback=progress_cb,
                    completion_callback=completion_cb
                )
                
                self.task_queue.task_done()
                
            except Exception as e:
                if str(e) != "":  # Ignore timeout exceptions
                    logger.error(f"Processing loop error: {e}")
                
            # Small sleep to prevent CPU spinning
            time.sleep(0.1)
        
        logger.info("Processing loop stopped")
    
    def get_queue_size(self) -> int:
        """Get number of pending tasks"""
        return self.task_queue.qsize()
    
    def is_active(self) -> bool:
        """Check if processor is running"""
        return self.is_processing
