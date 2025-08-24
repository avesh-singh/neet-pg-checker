"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type ProcessedFile = {
  id: number;
  filename: string;
  fileType: string;
  recordsCount: number;
  verificationStatus: string;
  sampleSize?: number;
  verificationRecordsCount: number;
  verificationProgress: number;
  processedDate: string;
};

type VerificationRecord = {
  id: number;
  pageNumber: number;
  verificationStatus: string;
  notes?: string;
  counsellingData: {
    rank: number;
    collegeName: string;
    course: string;
    quota: string;
    category: string;
    studentName?: string;
  };
  processedFile: {
    filename: string;
    fileType: string;
  };
};

export function VerificationDashboard() {
  const [files, setFiles] = useState<ProcessedFile[]>([]);
  const [verificationRecords, setVerificationRecords] = useState<VerificationRecord[]>([]);
  const [selectedFile, setSelectedFile] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [verifyingRecord, setVerifyingRecord] = useState<number | null>(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  useEffect(() => {
    if (selectedFile) {
      fetchVerificationRecords(selectedFile);
    }
  }, [selectedFile]);

  const fetchFiles = async () => {
    try {
      const response = await fetch("/api/verification/files");
      const data = await response.json();
      if (data.success) {
        setFiles(data.files);
      }
    } catch (error) {
      console.error("Failed to fetch files:", error);
    }
  };

  const fetchVerificationRecords = async (fileId: number) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/verification/records?fileId=${fileId}`);
      const data = await response.json();
      if (data.success) {
        setVerificationRecords(data.records);
      }
    } catch (error) {
      console.error("Failed to fetch verification records:", error);
    } finally {
      setLoading(false);
    }
  };

  const createSample = async (fileId: number, sampleRate: number = 0.1) => {
    try {
      const response = await fetch("/api/verification/sample", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fileId, sampleRate }),
      });
      const data = await response.json();
      if (data.success) {
        fetchFiles();
        if (selectedFile === fileId) {
          fetchVerificationRecords(fileId);
        }
      }
    } catch (error) {
      console.error("Failed to create sample:", error);
    }
  };

  const verifyRecord = async (recordId: number, status: string, notes?: string) => {
    setVerifyingRecord(recordId);
    try {
      const response = await fetch(`/api/verification/records/${recordId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          notes,
          verifiedBy: "Admin", // In production, get from auth session
        }),
      });
      const data = await response.json();
      if (data.success) {
        setVerificationRecords(prev =>
          prev.map(record =>
            record.id === recordId
              ? { ...record, verificationStatus: status, notes }
              : record
          )
        );
      }
    } catch (error) {
      console.error("Failed to verify record:", error);
    } finally {
      setVerifyingRecord(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">PDF Data Verification</h2>
        <p className="text-gray-600">
          Verify extracted data accuracy using sampling-based approach
        </p>
      </div>

      {/* Files Overview */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Processed Files</h3>
        <div className="space-y-3">
          {files.map((file) => (
            <div
              key={file.id}
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                selectedFile === file.id
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
              onClick={() => setSelectedFile(file.id)}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-medium">{file.filename}</h4>
                  <p className="text-sm text-gray-600">
                    {file.recordsCount} records • {file.fileType}
                  </p>
                  <p className="text-sm">
                    Status: <span className={`font-medium ${
                      file.verificationStatus === 'verified' ? 'text-green-600' : 'text-yellow-600'
                    }`}>
                      {file.verificationStatus}
                    </span>
                  </p>
                </div>
                <div className="text-right">
                  {file.sampleSize ? (
                    <div>
                      <p className="text-sm">Sample: {file.sampleSize} records</p>
                      <p className="text-sm">Progress: {file.verificationProgress}%</p>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        createSample(file.id);
                      }}
                    >
                      Create Sample
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Verification Records */}
      {selectedFile && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">
            Verification Records
            {loading && <span className="text-sm text-gray-500 ml-2">(Loading...)</span>}
          </h3>
          
          {verificationRecords.length === 0 ? (
            <p className="text-gray-500">No verification records found for this file.</p>
          ) : (
            <div className="space-y-4">
              {verificationRecords.map((record) => (
                <div
                  key={record.id}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium">
                        Page {record.pageNumber} • Rank {record.counsellingData.rank}
                      </h4>
                      <p className="text-sm text-gray-600">
                        {record.counsellingData.collegeName}
                      </p>
                      <p className="text-sm text-gray-600">
                        {record.counsellingData.course}
                      </p>
                      <p className="text-sm">
                        {record.counsellingData.quota} • {record.counsellingData.category}
                      </p>
                      {record.counsellingData.studentName && (
                        <p className="text-sm text-gray-600">
                          Student: {record.counsellingData.studentName}
                        </p>
                      )}
                    </div>
                    
                    <div className="text-right space-y-2">
                      <div className={`text-sm font-medium ${
                        record.verificationStatus === 'verified' ? 'text-green-600' :
                        record.verificationStatus === 'rejected' ? 'text-red-600' :
                        'text-yellow-600'
                      }`}>
                        {record.verificationStatus}
                      </div>
                      
                      {record.verificationStatus === 'pending' && (
                        <div className="space-x-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-green-600 border-green-600"
                            disabled={verifyingRecord === record.id}
                            onClick={() => verifyRecord(record.id, "verified")}
                          >
                            ✓ Verify
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600 border-red-600"
                            disabled={verifyingRecord === record.id}
                            onClick={() => verifyRecord(record.id, "rejected", "Data mismatch")}
                          >
                            ✗ Reject
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {record.notes && (
                    <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                      Notes: {record.notes}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}