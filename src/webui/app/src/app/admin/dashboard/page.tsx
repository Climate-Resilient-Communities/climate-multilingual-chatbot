"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Loader2,
  ThumbsUp,
  ThumbsDown,
  BarChart3,
  Users,
  TrendingUp,
  AlertCircle,
} from "lucide-react";

interface AnalyticsData {
  summary: {
    total_feedback: number;
    thumbs_up: number;
    thumbs_down: number;
    positive_percentage: number;
    negative_percentage: number;
    unrated: number;
  };
  sheet_info: {
    sheets_id: string;
    worksheet_title: string;
    last_updated: string;
  };
}

function DashboardContent() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const searchParams = useSearchParams();

  const fetchAnalytics = async (password: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:8001/admin/analytics?password=${encodeURIComponent(
          password
        )}`
      );

      // print the response object for debugging
      console.log("Response:", response);

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Invalid admin credentials");
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const analyticsData = await response.json();
      setData(analyticsData);
      setAuthenticated(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unknown error occurred"
      );
      setAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const password = searchParams.get("password");
    if (password) {
      fetchAnalytics(password);
    }
  }, [searchParams]);

  const handleRefresh = () => {
    const password = searchParams.get("password");
    if (password) {
      fetchAnalytics(password);
    }
  };

  if (!authenticated && !loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-500" />
              Access Denied
            </CardTitle>
            <CardDescription>
              Admin credentials required to view this dashboard.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alert>
              <AlertDescription>
                Please use the admin link from the main application to access
                this dashboard.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                <BarChart3 className="h-8 w-8 text-blue-600" />
                MLCC Analytics Dashboard
              </h1>
              <p className="text-gray-600 mt-1">
                Real-time feedback insights from Google Sheets
              </p>
            </div>
            <Button
              onClick={handleRefresh}
              disabled={loading}
              variant="outline"
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Refresh Data
            </Button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <Alert className="mb-6" variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {loading && !data && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">
              Loading analytics data...
            </span>
          </div>
        )}

        {/* Dashboard Content */}
        {data && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Total Feedback
                  </CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {data.summary?.total_feedback?.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    User responses collected
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Thumbs Up
                  </CardTitle>
                  <ThumbsUp className="h-4 w-4 text-green-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    {data.summary.thumbs_up.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {data.summary.positive_percentage}% of total feedback
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Thumbs Down
                  </CardTitle>
                  <ThumbsDown className="h-4 w-4 text-red-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600">
                    {data.summary.thumbs_down?.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {data.summary.negative_percentage}% of total feedback
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Satisfaction Rate
                  </CardTitle>
                  <TrendingUp className="h-4 w-4 text-blue-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600">
                    {data.summary.total_feedback > 0
                      ? Math.round(
                          (data.summary.thumbs_up /
                            (data.summary.thumbs_up +
                              data.summary.thumbs_down)) *
                            100
                        )
                      : 0}
                    %
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Positive vs negative ratio
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Detailed Analytics */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Feedback Breakdown</CardTitle>
                  <CardDescription>
                    Distribution of user feedback responses
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ThumbsUp className="h-4 w-4 text-green-600" />
                        <span className="text-sm font-medium">
                          Positive Feedback
                        </span>
                      </div>
                      <div className="text-right">
                        <Badge variant="secondary" className="text-green-600">
                          {data.summary.thumbs_up} (
                          {data.summary.positive_percentage}%)
                        </Badge>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ThumbsDown className="h-4 w-4 text-red-600" />
                        <span className="text-sm font-medium">
                          Negative Feedback
                        </span>
                      </div>
                      <div className="text-right">
                        <Badge variant="secondary" className="text-red-600">
                          {data.summary.thumbs_down} (
                          {data.summary.negative_percentage}%)
                        </Badge>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="h-4 w-4 rounded-full bg-gray-400" />
                        <span className="text-sm font-medium">Unrated</span>
                      </div>
                      <div className="text-right">
                        <Badge variant="outline">
                          {data.summary.unrated} (
                          {Math.round(
                            (data.summary.unrated /
                              data.summary.total_feedback) *
                              100
                          )}
                          %)
                        </Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Data Source</CardTitle>
                  <CardDescription>
                    Google Sheets integration details
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-500">
                        Sheets ID
                      </label>
                      <p className="text-sm font-mono bg-gray-100 p-2 rounded">
                        {data.sheet_info.sheets_id}
                      </p>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-500">
                        Worksheet
                      </label>
                      <p className="text-sm">
                        {data.sheet_info.worksheet_title}
                      </p>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-500">
                        Last Updated
                      </label>
                      <p className="text-sm">
                        {new Date(
                          data.sheet_info.last_updated
                        ).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
