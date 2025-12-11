"""
Advanced Thread Pool Manager for Profile Processing

Features:
- Global thread pool shared across all ticker processing
- Work-stealing: idle threads help with long-running tasks
- Non-blocking UI: all processing isolated from main thread
- Smart task distribution: balance load across threads
- Graceful cancellation and resource cleanup
"""
import logging
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger("thread_pool_manager")


class TaskPriority(Enum):
    """Task priority levels"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a processing task"""
    id: str
    ticker: str
    task_type: str  # 'filing_metadata', 'relationships', etc.
    func: Callable
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    future: Optional[Future] = None
    result: Any = None
    error: Optional[Exception] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time for running task"""
        if self.started_at:
            end = self.completed_at or time.time()
            return end - self.started_at
        return 0.0


class GlobalThreadPoolManager:
    """
    Global thread pool manager that efficiently distributes work across all available threads.
    
    Key Features:
    - Single global thread pool (e.g., 16 threads for 2 CPUs * 8 cores)
    - Work-stealing: idle threads pick up tasks from any ticker
    - Task prioritization
    - Progress tracking per ticker
    - Graceful cancellation
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern - only one pool manager"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, max_workers: int = 16):
        """
        Initialize global thread pool.
        
        Args:
            max_workers: Total threads available (default: 16)
        """
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="GlobalWorker"
        )
        
        # Task tracking
        self.pending_tasks: queue.PriorityQueue = queue.PriorityQueue()
        self.running_tasks: Dict[str, Task] = {}  # task_id -> Task
        self.completed_tasks: Dict[str, Task] = {}
        self.cancelled_tickers: set = set()
        
        # Ticker-specific tracking
        self.ticker_tasks: Dict[str, List[str]] = {}  # ticker -> [task_ids]
        self.ticker_progress: Dict[str, Dict] = {}  # ticker -> {total, completed, failed}
        
        # Locks for thread safety
        self.tasks_lock = threading.Lock()
        self.ticker_lock = threading.Lock()
        
        # Dispatcher thread
        self.dispatcher_running = False
        self.dispatcher_thread = None
        
        logger.info(f"GlobalThreadPoolManager initialized with {max_workers} workers")
    
    def start_dispatcher(self):
        """Start the task dispatcher thread"""
        if self.dispatcher_running:
            return
        
        self.dispatcher_running = True
        self.dispatcher_thread = threading.Thread(
            target=self._dispatcher_loop,
            daemon=True,
            name="TaskDispatcher"
        )
        self.dispatcher_thread.start()
        logger.info("Task dispatcher started")
    
    def stop_dispatcher(self):
        """Stop the task dispatcher"""
        self.dispatcher_running = False
        if self.dispatcher_thread:
            self.dispatcher_thread.join(timeout=2)
        logger.info("Task dispatcher stopped")
    
    def _dispatcher_loop(self):
        """
        Dispatcher loop - continuously submits pending tasks to thread pool.
        This ensures threads are always busy with available work.
        """
        while self.dispatcher_running:
            try:
                # Check if we have capacity
                with self.tasks_lock:
                    running_count = len(self.running_tasks)
                    available_slots = self.max_workers - running_count
                
                if available_slots > 0:
                    try:
                        # Get highest priority task
                        priority, task_id, task = self.pending_tasks.get(timeout=0.1)
                        
                        # Check if task's ticker was cancelled
                        if task.ticker in self.cancelled_tickers:
                            task.status = TaskStatus.CANCELLED
                            continue
                        
                        # Submit to thread pool
                        task.future = self.executor.submit(self._execute_task, task)
                        task.status = TaskStatus.RUNNING
                        task.started_at = time.time()
                        
                        with self.tasks_lock:
                            self.running_tasks[task.id] = task
                        
                        logger.debug(f"Dispatched task {task.id} ({task.task_type}) for {task.ticker}")
                        
                    except queue.Empty:
                        # No pending tasks
                        time.sleep(0.1)
                else:
                    # All threads busy, wait
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Dispatcher error: {e}")
                time.sleep(0.5)
    
    def _execute_task(self, task: Task) -> Any:
        """Execute a task and handle result/error"""
        try:
            logger.debug(f"Executing {task.task_type} for {task.ticker}")
            result = task.func()
            task.result = result
            task.status = TaskStatus.COMPLETED
            return result
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.error = e
            task.status = TaskStatus.FAILED
            raise
        finally:
            task.completed_at = time.time()
            
            # Move from running to completed
            with self.tasks_lock:
                if task.id in self.running_tasks:
                    del self.running_tasks[task.id]
                self.completed_tasks[task.id] = task
            
            # Update ticker progress
            with self.ticker_lock:
                if task.ticker in self.ticker_progress:
                    if task.status == TaskStatus.COMPLETED:
                        self.ticker_progress[task.ticker]['completed'] += 1
                    elif task.status == TaskStatus.FAILED:
                        self.ticker_progress[task.ticker]['failed'] += 1
    
    def submit_ticker_tasks(
        self,
        ticker: str,
        tasks: List[Callable],
        task_names: List[str],
        callback: Optional[Callable[[str, str, Any], None]] = None
    ) -> List[str]:
        """
        Submit all tasks for a ticker.
        
        Args:
            ticker: Ticker symbol
            tasks: List of task functions
            task_names: Names of tasks (for tracking)
            callback: Progress callback (ticker, task_name, result)
            
        Returns:
            List of task IDs
        """
        task_ids = []
        
        # Initialize ticker tracking
        with self.ticker_lock:
            self.ticker_tasks[ticker] = []
            self.ticker_progress[ticker] = {
                'total': len(tasks),
                'completed': 0,
                'failed': 0,
                'started_at': time.time()
            }
        
        # Create and queue tasks
        for i, (task_func, task_name) in enumerate(zip(tasks, task_names)):
            task_id = f"{ticker}_{task_name}_{int(time.time()*1000)}"
            
            # Wrap function to include callback
            def wrapped_func(func=task_func, name=task_name):
                result = func()
                if callback:
                    callback(ticker, name, result)
                return result
            
            task = Task(
                id=task_id,
                ticker=ticker,
                task_type=task_name,
                func=wrapped_func,
                priority=TaskPriority.NORMAL
            )
            
            # Add to pending queue (priority, task_id, task)
            self.pending_tasks.put((task.priority.value, task_id, task))
            task_ids.append(task_id)
            
            with self.ticker_lock:
                self.ticker_tasks[ticker].append(task_id)
        
        logger.info(f"Queued {len(tasks)} tasks for {ticker}")
        return task_ids
    
    def wait_for_ticker(self, ticker: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for all tasks of a ticker to complete.
        
        Args:
            ticker: Ticker symbol
            timeout: Max wait time in seconds
            
        Returns:
            Dict with results {task_name: result}
        """
        start_time = time.time()
        results = {}
        
        while True:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Timeout waiting for {ticker}")
                break
            
            # Check if all tasks completed
            with self.ticker_lock:
                if ticker not in self.ticker_progress:
                    break
                
                progress = self.ticker_progress[ticker]
                total = progress['total']
                completed = progress['completed'] + progress['failed']
                
                if completed >= total:
                    # All done
                    break
            
            time.sleep(0.1)
        
        # Collect results
        with self.ticker_lock:
            if ticker in self.ticker_tasks:
                for task_id in self.ticker_tasks[ticker]:
                    if task_id in self.completed_tasks:
                        task = self.completed_tasks[task_id]
                        results[task.task_type] = task.result
        
        return results
    
    def cancel_ticker(self, ticker: str):
        """Cancel all tasks for a ticker"""
        self.cancelled_tickers.add(ticker)
        
        # Cancel running tasks
        with self.tasks_lock:
            for task_id, task in list(self.running_tasks.items()):
                if task.ticker == ticker and task.future:
                    task.future.cancel()
                    task.status = TaskStatus.CANCELLED
        
        logger.info(f"Cancelled all tasks for {ticker}")
    
    def cancel_all(self):
        """Cancel all pending and running tasks"""
        # Cancel all tickers
        with self.ticker_lock:
            all_tickers = list(self.ticker_tasks.keys())
        
        for ticker in all_tickers:
            self.cancel_ticker(ticker)
        
        logger.info("Cancelled all tasks")
    
    def get_ticker_progress(self, ticker: str) -> Dict[str, Any]:
        """Get progress info for a ticker"""
        with self.ticker_lock:
            if ticker in self.ticker_progress:
                progress = self.ticker_progress[ticker].copy()
                if 'started_at' in progress:
                    progress['elapsed'] = time.time() - progress['started_at']
                return progress
        return {}
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get overall pool statistics"""
        with self.tasks_lock:
            running = len(self.running_tasks)
            
        pending_count = self.pending_tasks.qsize()
        
        with self.tasks_lock:
            completed = len(self.completed_tasks)
        
        return {
            'max_workers': self.max_workers,
            'running_tasks': running,
            'pending_tasks': pending_count,
            'completed_tasks': completed,
            'utilization': f"{(running / self.max_workers) * 100:.1f}%",
            'idle_threads': self.max_workers - running
        }
    
    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool"""
        self.stop_dispatcher()
        self.executor.shutdown(wait=wait)
        logger.info("Thread pool shut down")


# Global instance
_global_pool_manager = None


def get_thread_pool_manager(max_workers: int = 16) -> GlobalThreadPoolManager:
    """Get or create global thread pool manager"""
    global _global_pool_manager
    if _global_pool_manager is None:
        _global_pool_manager = GlobalThreadPoolManager(max_workers)
        _global_pool_manager.start_dispatcher()
    return _global_pool_manager
