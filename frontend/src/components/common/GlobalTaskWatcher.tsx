import React, { useEffect, useRef } from 'react';
import { notification, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTaskStore } from '../../stores/taskStore';
import { useEditorStore } from '../../stores/editorStore';
import { taskService, documentService } from '../../api/services';

const MAX_RETRY_ATTEMPTS = 3;
const RETRY_WINDOW_MS = 30000;

const MAX_CONCURRENT_SSE = 5;

const GlobalTaskWatcher: React.FC = () => {
  const { activeTaskIds, removeTask } = useTaskStore();
  const { setAiPolishedContent, setViewMode, setBusy, currentDocId } = useEditorStore();
  const eventSources = useRef<Record<string, EventSource>>({});
  const retryCounts = useRef<Record<string, { count: number; firstAttempt: number }>>({});
  const pollingIntervals = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const navigate = useNavigate();

  useEffect(() => {
    // Determine how many tasks need SSE vs polling due to quota
    let sseCount = Object.keys(eventSources.current).length;

    // Watch for new tasks in activeTaskIds
    activeTaskIds.forEach((taskId: string) => {
      if (!eventSources.current[taskId] && !pollingIntervals.current[taskId]) {
        if (sseCount < MAX_CONCURRENT_SSE) {
          establishSSE(taskId);
          sseCount++;
        } else {
          console.warn(`SSE pool full (max ${MAX_CONCURRENT_SSE}). Falling back to polling for task ${taskId}.`);
          notification.warning({
            message: '连接池已满',
            description: '任务连接数过多，已切换为轮询补偿模式排队。',
            duration: 4,
          });
          startPolling(taskId);
        }
      }
    });

    // Cleanup closed tasks
    Object.keys(eventSources.current).forEach((taskId: string) => {
      if (!activeTaskIds.includes(taskId)) {
        eventSources.current[taskId].close();
        delete eventSources.current[taskId];
      }
    });

    Object.keys(pollingIntervals.current).forEach((taskId: string) => {
      if (!activeTaskIds.includes(taskId)) {
        clearInterval(pollingIntervals.current[taskId]);
        delete pollingIntervals.current[taskId];
      }
    });

    return () => {
      Object.values(eventSources.current).forEach(es => es.close());
      Object.values(pollingIntervals.current).forEach(timer => clearInterval(timer));
    };
  }, [activeTaskIds]);

  const establishSSE = async (taskId: string, backoffMs: number = 2000) => {
    try {
      const { ticket } = await taskService.getTicket(taskId);
      const es = new EventSource(`/api/v1/sse/${taskId}/events?ticket=${ticket}`);
      eventSources.current[taskId] = es;

      es.addEventListener('task.completed', (e: any) => {
        const data = JSON.parse(e.data);
        showSuccessNotification(data);
        if (data.doc_id === currentDocId) {
          documentService.getDetail(data.doc_id).then(res => {
            setAiPolishedContent(res.ai_polished_content || res.draft_suggestion || null);
            setViewMode('DIFF');
            setBusy(false);
          });
        }
        cleanupTask(taskId);
      });

      es.addEventListener('task.failed', (e: any) => {
        const data = JSON.parse(e.data);
        notification.error({
          message: '任务失败',
          description: data.error_message,
        });
        cleanupTask(taskId);
      });

      es.onerror = () => {
        es.close();
        delete eventSources.current[taskId];
        
        // Handle controlled reconnection logic (Section V.3.4)
        handleReconnection(taskId, backoffMs);
      };
    } catch (err) {
      console.error('Failed to establish SSE:', err);
      handleReconnection(taskId, backoffMs);
    }
  };

  const handleReconnection = (taskId: string, currentBackoff: number) => {
    const now = Date.now();
    const retryInfo = retryCounts.current[taskId] || { count: 0, firstAttempt: now };
    
    // Reset window if needed
    if (now - retryInfo.firstAttempt > RETRY_WINDOW_MS) {
      retryInfo.count = 1;
      retryInfo.firstAttempt = now;
    } else {
      retryInfo.count += 1;
    }
    retryCounts.current[taskId] = retryInfo;

    if (retryInfo.count > MAX_RETRY_ATTEMPTS) {
      console.warn(`SSE reconnection failed too many times for task ${taskId}. Falling back to polling.`);
      notification.warning({
        message: '实时连接不稳定',
        description: '已自动切换为轮询补偿模式。',
        duration: 4,
      });
      startPolling(taskId);
    } else {
      const nextBackoff = Math.min(currentBackoff * 2, 30000);
      setTimeout(() => {
        if (activeTaskIds.includes(taskId)) {
          establishSSE(taskId, nextBackoff);
        }
      }, currentBackoff);
    }
  };

  const startPolling = (taskId: string) => {
    if (pollingIntervals.current[taskId]) return;

    let pollBackoff = 2000;
    const poll = async () => {
      try {
        const res = await taskService.getStatus(taskId);
        if (res.task_status === 'COMPLETED') {
          showSuccessNotification({
            doc_id: res.doc_id,
            type: res.task_type,
            result_summary: res.result_summary
          });
          cleanupTask(taskId);
        } else if (res.task_status === 'FAILED') {
          notification.error({
            message: '任务失败',
            description: res.error_message,
          });
          cleanupTask(taskId);
        } else {
          // Continue polling with exponential backoff up to 30s
          pollBackoff = Math.min(pollBackoff * 2, 30000);
          pollingIntervals.current[taskId] = setTimeout(poll, pollBackoff);
        }
      } catch (err) {
        pollBackoff = Math.min(pollBackoff * 2, 30000);
        pollingIntervals.current[taskId] = setTimeout(poll, pollBackoff);
      }
    };

    pollingIntervals.current[taskId] = setTimeout(poll, pollBackoff);
  };

  const cleanupTask = (taskId: string) => {
    if (eventSources.current[taskId]) {
      eventSources.current[taskId].close();
      delete eventSources.current[taskId];
    }
    if (pollingIntervals.current[taskId]) {
      clearTimeout(pollingIntervals.current[taskId] as any);
      delete pollingIntervals.current[taskId];
    }
    delete retryCounts.current[taskId];
    removeTask(taskId);
  };

  const showSuccessNotification = (data: any) => {
    const { doc_id, type } = data;
    notification.success({
      message: type === 'POLISH' ? 'AI 润色已完成' : '排版已完成',
      description: '点击查看详情或下载产物。',
      btn: (
        <Button type="primary" size="small" onClick={() => navigate(`/workspace/${doc_id}`)}>
          查看详情
        </Button>
      ),
    });
  };

  return null;
};

export default GlobalTaskWatcher;
