"use client";

import { useState, useEffect } from "react";

interface TracesPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TracesPanel({ isOpen, onClose }: TracesPanelProps) {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const fetchLogs = async () => {
      try {
        setLoading(true);
        const response = await fetch("/api/factory/logs");
        const data = await response.json();
        if (data.success) {
          setWorkflows(data.workflows);
        }
      } catch (error) {
        console.error("Failed to fetch logs:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);

    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="absolute inset-y-0 right-0 w-full bg-white shadow-lg z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gray-50">
        <h2 className="text-lg font-semibold text-gray-900">Workflow Logs</h2>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-200 rounded transition"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {loading && workflows.length === 0 ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600">Loading workflows...</p>
          </div>
        ) : workflows.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-4 text-gray-600">No workflows yet</p>
            <p className="text-sm text-gray-400">Start a workflow to see logs here</p>
          </div>
        ) : (
          workflows.map((workflow) => (
            <div key={workflow.trace_id} className="border border-gray-200 rounded-lg overflow-hidden">
              {/* Workflow Header */}
              <div className="bg-gray-50 p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">{workflow.user_task}</h3>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    workflow.status === "completed" ? "bg-green-100 text-green-700" :
                    workflow.status === "running" ? "bg-blue-100 text-blue-700 animate-pulse" :
                    workflow.status === "failed" ? "bg-red-100 text-red-700" :
                    "bg-gray-100 text-gray-700"
                  }`}>
                    {workflow.status}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1 font-mono">{workflow.trace_id}</p>
              </div>

              {/* Logs Timeline */}
              <div className="p-4 space-y-3">
                {workflow.logs.map((log: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-3 group">
                    {/* Timeline dot */}
                    <div className="flex flex-col items-center">
                      <div className={`w-2 h-2 rounded-full mt-1.5 ${
                        log.type === "success" ? "bg-green-500" :
                        log.type === "error" ? "bg-red-500" :
                        log.type === "warning" ? "bg-yellow-500" :
                        "bg-blue-500"
                      }`}></div>
                      {idx < workflow.logs.length - 1 && (
                        <div className="w-0.5 h-full bg-gray-200 mt-1"></div>
                      )}
                    </div>

                    {/* Log content */}
                    <div className="flex-1 pb-4">
                      <div className="flex items-start justify-between gap-2">
                        <span className={`text-sm ${
                          log.type === "success" ? "text-green-700 font-medium" :
                          log.type === "error" ? "text-red-700 font-medium" :
                          log.type === "warning" ? "text-yellow-700" :
                          "text-gray-700"
                        }`}>
                          {log.message}
                        </span>
                        <span className="text-xs text-gray-400 whitespace-nowrap">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      
                      {log.data && (
                        <pre className="mt-2 p-3 bg-gray-50 rounded text-xs overflow-auto border border-gray-200">
                          {typeof log.data === "string" 
                            ? log.data 
                            : JSON.stringify(log.data, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}