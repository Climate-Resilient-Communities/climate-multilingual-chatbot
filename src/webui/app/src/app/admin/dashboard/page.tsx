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
  MessageSquare,
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
  manual_feedback: {
    entries: ManualFeedbackEntry[];
    count: number;
  };
  category_breakdown: {
    thumbs_up: {
      instructions: number;
      comprehensive: number;
      translation: number;
      expected: number;
      other: number;
    };
    thumbs_down: {
      instructions: number;
      "no-response": number;
      unrelated: number;
      translation: number;
      "guard-filter": number;
      other: number;
    };
  };
  additional_feedback: AdditionalFeedback[];
  cost_analytics?: {
    total_cost: number;
    total_interactions: number;
    model_breakdown: {
      [key: string]: {
        interactions: number;
        cost: number;
        input_tokens: number;
        output_tokens: number;
      };
    };
    cost_summary: {
      cohere_cost: number;
      nova_cost: number;
      pinecone_cost: number;
    };
    recent_interactions: RecentInteraction[];
    interaction_breakdown: {
      [key: string]: number;
    };
    language_breakdown: {
      [key: string]: number;
    };
    detailed_queries?: {
      on_topic: DetailedQuery[];
      off_topic: DetailedQuery[];
      harmful: DetailedQuery[];
    };
  };
}

interface AdditionalFeedback {
  timestamp: string;
  type: "positive" | "negative" | string;
  comment: string;
}

interface RecentInteraction {
  timestamp: string;
  session_id: string;
  model: string;
  language: string;
  query_type: string;
  cost: number;
  processing_time: number;
  cache_hit: boolean;
  query_text?: string;
  classification?: "on-topic" | "off-topic" | "harmful";
  safety_score?: number;
}

interface ManualFeedbackEntry {
  timestamp: string;
  feedback_type: string;
  language: string;
  description: string;
  bug_details: string;
  evidence: string;
  usage_frequency: string;
}

interface DetailedQuery {
  id: string;
  timestamp: string;
  session_id: string;
  query_text: string;
  classification: "on-topic" | "off-topic" | "harmful";
  safety_score: number;
  language: string;
  model: string;
  response_generated: boolean;
  blocked_reason?: string;
}

function DashboardContent() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const searchParams = useSearchParams();

  const fetchAnalytics = async (password: string) => {
    setLoading(true);
    setError(null);

    try {
      // Try new secure endpoint first with Authorization header
      let response = await fetch(`/api/v1/admin/analytics`, {
        headers: {
          Authorization: `Bearer ${password}`,
          "Content-Type": "application/json",
        },
      });

      // Fallback to standalone admin API if main API is not available
      if (!response.ok && response.status === 404) {
        response = await fetch(
          `http://localhost:8001/admin/analytics?password=${encodeURIComponent(
            password
          )}`
        );
      }

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
      
      // Store token securely in sessionStorage for subsequent requests
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('adminToken', password);
        setAdminToken(password);
        
        // Clean URL by removing password parameter if present
        if (searchParams.get("password")) {
          const url = new URL(window.location.href);
          url.searchParams.delete("password");
          window.history.replaceState({}, '', url);
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unknown error occurred"
      );
      setAuthenticated(false);
      // Clear any stored token on auth failure
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('adminToken');
        setAdminToken(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Check for admin token in sessionStorage first (for returning users)
    if (typeof window !== 'undefined') {
      const storedToken = sessionStorage.getItem('adminToken');
      if (storedToken) {
        setAdminToken(storedToken);
        fetchAnalytics(storedToken);
        return;
      }
    }

    // Fallback to URL parameter (for initial authentication)
    const password = searchParams.get("password");
    if (password) {
      fetchAnalytics(password);
    }
  }, [searchParams]);

  const handleRefresh = () => {
    const token = adminToken || (typeof window !== 'undefined' ? sessionStorage.getItem('adminToken') : null);
    if (token) {
      fetchAnalytics(token);
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
            <div className="flex items-center gap-2">
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
              <Button
                onClick={() => {
                  if (typeof window !== 'undefined') {
                    sessionStorage.removeItem('adminToken');
                    setAdminToken(null);
                    setAuthenticated(false);
                    setData(null);
                    // Redirect to main app or close tab
                    window.location.href = '/';
                  }
                }}
                variant="outline"
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                Logout
              </Button>
            </div>
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
                  <ThumbsUp className="h-4 w-4 text-green-700" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-800">
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
                    Distribution of user feedback responses with detailed
                    categories
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ThumbsUp className="h-4 w-4 text-green-700" />
                        <span className="text-sm font-medium">
                          Positive Feedback
                        </span>
                      </div>
                      <div className="text-right">
                        <Badge
                          variant="secondary"
                          className="text-green-800 bg-green-100"
                        >
                          {data.summary.thumbs_up} (
                          {data.summary.positive_percentage}%)
                        </Badge>
                      </div>
                    </div>

                    {/* Positive Feedback Categories */}
                    {data.category_breakdown &&
                      Object.keys(data.category_breakdown.thumbs_up).length >
                        0 && (
                        <div className="ml-6 space-y-1">
                          {Object.entries(
                            data.category_breakdown.thumbs_up
                          ).map(([category, count]) => (
                            <div
                              key={category}
                              className="flex items-center justify-between text-xs"
                            >
                              <span className="text-gray-600 capitalize">
                                {category}
                              </span>
                              <Badge
                                variant="outline"
                                className="text-green-700 bg-green-50"
                              >
                                {count as number}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      )}

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ThumbsDown className="h-4 w-4 text-red-600" />
                        <span className="text-sm font-medium">
                          Negative Feedback
                        </span>
                      </div>
                      <div className="text-right">
                        <Badge
                          variant="secondary"
                          className="text-red-600 bg-red-100"
                        >
                          {data.summary.thumbs_down} (
                          {data.summary.negative_percentage}%)
                        </Badge>
                      </div>
                    </div>

                    {/* Negative Feedback Categories */}
                    {data.category_breakdown &&
                      Object.keys(data.category_breakdown.thumbs_down).length >
                        0 && (
                        <div className="ml-6 space-y-1">
                          {Object.entries(
                            data.category_breakdown.thumbs_down
                          ).map(([category, count]) => (
                            <div
                              key={category}
                              className="flex items-center justify-between text-xs"
                            >
                              <span className="text-gray-600 capitalize">
                                {category}
                              </span>
                              <Badge
                                variant="outline"
                                className="text-red-600 bg-red-50"
                              >
                                {count as number}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      )}
                  </div>
                </CardContent>
              </Card>

              {/* Additional Feedback Comments */}
              {data.additional_feedback &&
                data.additional_feedback.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <MessageSquare className="h-5 w-5" />
                        Recent Comments ({data.additional_feedback.length})
                      </CardTitle>
                      <CardDescription>
                        Latest user feedback with additional details
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 max-h-80 overflow-y-auto">
                        {data.additional_feedback
                          .slice(0, 10)
                          .map((feedback, index) => (
                            <div
                              key={index}
                              className="border-l-2 border-blue-200 pl-3 py-2"
                            >
                              <div className="flex items-center gap-2 mb-1">
                                {feedback.type === "positive" && (
                                  <ThumbsUp className="h-3 w-3 text-green-600" />
                                )}
                                {feedback.type === "negative" && (
                                  <ThumbsDown className="h-3 w-3 text-red-600" />
                                )}
                                <span className="text-xs text-gray-500">
                                  {new Date(
                                    feedback.timestamp
                                  ).toLocaleDateString()}
                                </span>
                              </div>
                              <p className="text-sm text-gray-700">
                                {feedback.comment}
                              </p>
                            </div>
                          ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
            </div>

            {/* Manual Feedback Entries Table */}
            {data.manual_feedback && data.manual_feedback.count > 0 && (
              <div className="mt-8">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Users className="h-5 w-5" />
                      Manual Form Submissions ({data.manual_feedback.count})
                    </CardTitle>
                    <CardDescription>
                      Detailed feedback submitted through the feedback form
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left p-2 font-medium">Date</th>
                            <th className="text-left p-2 font-medium">Type</th>
                            <th className="text-left p-2 font-medium">
                              Language
                            </th>
                            <th className="text-left p-2 font-medium">
                              Description
                            </th>
                            <th className="text-left p-2 font-medium">Usage</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.manual_feedback.entries.map((entry, index) => (
                            <tr
                              key={index}
                              className="border-b hover:bg-gray-50"
                            >
                              <td className="p-2">
                                <div className="text-xs text-gray-500">
                                  {new Date(
                                    entry.timestamp
                                  ).toLocaleDateString()}
                                </div>
                                <div className="text-xs text-gray-400">
                                  {new Date(
                                    entry.timestamp
                                  ).toLocaleTimeString()}
                                </div>
                              </td>
                              <td className="p-2">
                                <Badge
                                  variant={
                                    entry.feedback_type.includes("Bug")
                                      ? "destructive"
                                      : entry.feedback_type.includes(
                                          "Enhancement"
                                        )
                                      ? "default"
                                      : "secondary"
                                  }
                                  className="text-xs"
                                >
                                  {entry.feedback_type.includes("Bug")
                                    ? "🐛 Bug"
                                    : entry.feedback_type.includes(
                                        "Enhancement"
                                      )
                                    ? "✨ Enhancement"
                                    : entry.feedback_type.includes("Question")
                                    ? "❓ Question"
                                    : "📝 Feedback"}
                                </Badge>
                              </td>
                              <td className="p-2 text-xs">{entry.language}</td>
                              <td className="p-2">
                                <div className="max-w-xs">
                                  <p className="text-xs text-gray-700 line-clamp-2">
                                    {entry.description}
                                  </p>
                                  {entry.bug_details &&
                                    entry.bug_details !== "Testing" && (
                                      <p className="text-xs text-gray-500 mt-1 italic">
                                        Bug:{" "}
                                        {entry.bug_details.substring(0, 50)}...
                                      </p>
                                    )}
                                </div>
                              </td>
                              <td className="p-2">
                                <Badge variant="outline" className="text-xs">
                                  {entry.usage_frequency}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Cost Analytics Section */}
            {data.cost_analytics && (
              <>
                {/* Cost Overview Cards */}
                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">
                        Total Cost
                      </CardTitle>
                      <div className="h-4 w-4 text-muted-foreground">💰</div>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        ${data.cost_analytics.total_cost.toFixed(4)}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        All-time spend
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">
                        Nova Cost
                      </CardTitle>
                      <div className="h-4 w-4 text-muted-foreground">🧠</div>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        ${data.cost_analytics.cost_summary.nova_cost.toFixed(4)}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        AWS Bedrock Nova
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">
                        Pinecone Cost
                      </CardTitle>
                      <div className="h-4 w-4 text-muted-foreground">🔍</div>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        $
                        {data.cost_analytics.cost_summary.pinecone_cost.toFixed(
                          4
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Vector operations
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">
                        Total Interactions
                      </CardTitle>
                      <BarChart3 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {data.cost_analytics.total_interactions.toLocaleString()}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Total queries processed
                      </p>
                    </CardContent>
                  </Card>
                </div>

                {/* Interaction Breakdown and Safety & Sentiment */}
                <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Interaction Breakdown</CardTitle>
                      <CardDescription>
                        Query types and categories
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(
                          data.cost_analytics.interaction_breakdown
                        )
                          .filter(([type]) => !["on-topic", "off-topic", "harmful"].includes(type))
                          .map(([type, count]) => (
                          <div
                            key={type}
                            className="flex items-center justify-between"
                          >
                            <span className="text-sm font-medium capitalize">
                              {type.replace("_", " ")}
                            </span>
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary">{count}</Badge>
                              <span className="text-xs text-gray-500">
                                {data.cost_analytics &&
                                data.cost_analytics.total_interactions > 0
                                  ? `${Math.round(
                                      (count /
                                        data.cost_analytics
                                          .total_interactions) *
                                        100
                                    )}%`
                                  : "0%"}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Safety & Sentiment</CardTitle>
                      <CardDescription>
                        Content filtering and user satisfaction
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="grid grid-cols-3 gap-4">
                          <div className="text-center p-3 border rounded-lg bg-green-50 border-green-200">
                            <div className="text-2xl font-bold text-green-600">
                              {data.cost_analytics.interaction_breakdown?.[
                                "on-topic"
                              ] || 0}
                            </div>
                            <div className="text-xs text-gray-600 font-medium">On-Topic</div>
                            <div className="text-xs text-gray-500">
                              {data.cost_analytics &&
                              data.cost_analytics.total_interactions > 0
                                ? `${Math.round(
                                    ((data.cost_analytics.interaction_breakdown?.["on-topic"] || 0) /
                                      data.cost_analytics.total_interactions) *
                                      100
                                  )}%`
                                : "0%"}
                            </div>
                          </div>
                          <div className="text-center p-3 border rounded-lg bg-orange-50 border-orange-200">
                            <div className="text-2xl font-bold text-orange-600">
                              {data.cost_analytics.interaction_breakdown?.[
                                "off-topic"
                              ] || 0}
                            </div>
                            <div className="text-xs text-gray-600 font-medium">Off-Topic</div>
                            <div className="text-xs text-gray-500">
                              {data.cost_analytics &&
                              data.cost_analytics.total_interactions > 0
                                ? `${Math.round(
                                    ((data.cost_analytics.interaction_breakdown?.["off-topic"] || 0) /
                                      data.cost_analytics.total_interactions) *
                                      100
                                  )}%`
                                : "0%"}
                            </div>
                          </div>
                          <div className="text-center p-3 border rounded-lg bg-red-50 border-red-200">
                            <div className="text-2xl font-bold text-red-600">
                              {data.cost_analytics.interaction_breakdown?.[
                                "harmful"
                              ] || 0}
                            </div>
                            <div className="text-xs text-gray-600 font-medium">Harmful</div>
                            <div className="text-xs text-gray-500">
                              {data.cost_analytics &&
                              data.cost_analytics.total_interactions > 0
                                ? `${Math.round(
                                    ((data.cost_analytics.interaction_breakdown?.["harmful"] || 0) /
                                      data.cost_analytics.total_interactions) *
                                      100
                                  )}%`
                                : "0%"}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Query Content Details */}
                <div className="mt-8">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <MessageSquare className="h-5 w-5" />
                        Query Content Details
                      </CardTitle>
                      <CardDescription>
                        Detailed breakdown of user queries by safety classification
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {/* On-Topic Queries */}
                        <div className="border rounded-lg p-4 bg-green-50 border-green-200">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="w-3 h-3 bg-green-600 rounded-full"></div>
                            <h4 className="font-semibold text-green-800">On-Topic Messages</h4>
                            <Badge className="bg-green-100 text-green-800">
                              {data.cost_analytics.interaction_breakdown?.["on-topic"] || 0}
                            </Badge>
                          </div>
                          <div className="max-h-64 overflow-y-auto space-y-2">
                            {data.cost_analytics?.detailed_queries?.on_topic && data.cost_analytics.detailed_queries.on_topic.length > 0 ? (
                              data.cost_analytics.detailed_queries.on_topic.slice(0, 5).map((query, index) => (
                                <div key={query.id} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      {query.session_id.substring(0, 8)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date(query.timestamp).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700 line-clamp-2">
                                    {query.query_text.substring(0, 100)}{query.query_text.length > 100 ? '...' : ''}
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="outline" className="text-xs">
                                      {query.language}
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      {query.model.replace("_", " ")}
                                    </Badge>
                                    <Badge className="text-xs bg-green-100 text-green-800">
                                      Score: {(query.safety_score * 100).toFixed(0)}%
                                    </Badge>
                                  </div>
                                </div>
                              ))
                            ) : data.cost_analytics.recent_interactions
                              ?.filter((interaction) => interaction.classification === "on-topic" || interaction.query_type === "climate_response")
                              .slice(0, 5)
                              .map((interaction, index) => (
                                <div key={index} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      {interaction.session_id?.substring(0, 8)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date(interaction.timestamp).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700">
                                    {interaction.query_text || "Climate-related question about environmental impacts..."}
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.language}
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.model.replace("_", " ")}
                                    </Badge>
                                  </div>
                                </div>
                              )).length > 0 ? data.cost_analytics.recent_interactions
                              ?.filter((interaction) => interaction.classification === "on-topic" || interaction.query_type === "climate_response")
                              .slice(0, 5)
                              .map((interaction, index) => (
                                <div key={index} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      {interaction.session_id?.substring(0, 8)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date(interaction.timestamp).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700">
                                    {interaction.query_text || "Climate-related question about environmental impacts..."}
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.language}
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.model.replace("_", " ")}
                                    </Badge>
                                  </div>
                                </div>
                              )) : (
                              <div className="text-center text-gray-500 py-4">
                                <p className="text-sm">No on-topic queries to display</p>
                                <p className="text-xs">Data will appear here when queries are classified</p>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Off-Topic Queries */}
                        <div className="border rounded-lg p-4 bg-orange-50 border-orange-200">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="w-3 h-3 bg-orange-600 rounded-full"></div>
                            <h4 className="font-semibold text-orange-800">Off-Topic Messages</h4>
                            <Badge className="bg-orange-100 text-orange-800">
                              {data.cost_analytics.interaction_breakdown?.["off-topic"] || 0}
                            </Badge>
                          </div>
                          <div className="max-h-64 overflow-y-auto space-y-2">
                            {data.cost_analytics?.detailed_queries?.off_topic && data.cost_analytics.detailed_queries.off_topic.length > 0 ? (
                              data.cost_analytics.detailed_queries.off_topic.slice(0, 3).map((query, index) => (
                                <div key={query.id} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      {query.session_id.substring(0, 8)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date(query.timestamp).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700 line-clamp-2">
                                    {query.query_text.substring(0, 100)}{query.query_text.length > 100 ? '...' : ''}
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="outline" className="text-xs">
                                      {query.language}
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      {query.model.replace("_", " ")}
                                    </Badge>
                                    <Badge className="text-xs bg-orange-100 text-orange-800">
                                      Score: {(query.safety_score * 100).toFixed(0)}%
                                    </Badge>
                                  </div>
                                </div>
                              ))
                            ) : data.cost_analytics?.recent_interactions
                              ?.filter((interaction) => interaction.classification === "off-topic" || interaction.query_type === "translation")
                              .slice(0, 3)
                              .map((interaction, index) => (
                                <div key={index} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      {interaction.session_id?.substring(0, 8)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date(interaction.timestamp).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700">
                                    {interaction.query_text || "Non-climate question about general topics..."}
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.language}
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.model.replace("_", " ")}
                                    </Badge>
                                  </div>
                                </div>
                              )).length > 0 ? data.cost_analytics.recent_interactions
                              ?.filter((interaction) => interaction.classification === "off-topic" || interaction.query_type === "translation")
                              .slice(0, 3)
                              .map((interaction, index) => (
                                <div key={index} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      {interaction.session_id?.substring(0, 8)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date(interaction.timestamp).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700">
                                    {interaction.query_text || "Non-climate question about general topics..."}
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.language}
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      {interaction.model.replace("_", " ")}
                                    </Badge>
                                  </div>
                                </div>
                              )) : (
                              <div className="text-center text-gray-500 py-4">
                                <p className="text-sm">No off-topic queries to display</p>
                                <p className="text-xs">Data will appear here when queries are classified</p>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Harmful Queries */}
                        <div className="border rounded-lg p-4 bg-red-50 border-red-200">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="w-3 h-3 bg-red-600 rounded-full"></div>
                            <h4 className="font-semibold text-red-800">Harmful/Blocked Messages</h4>
                            <Badge className="bg-red-100 text-red-800">
                              {data.cost_analytics.interaction_breakdown?.["harmful"] || 0}
                            </Badge>
                          </div>
                          <div className="max-h-64 overflow-y-auto space-y-2">
                            {data.cost_analytics?.detailed_queries?.harmful && data.cost_analytics.detailed_queries.harmful.length > 0 ? (
                              data.cost_analytics.detailed_queries.harmful.slice(0, 3).map((query, index) => (
                                <div key={query.id} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      {query.session_id.substring(0, 8)}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date(query.timestamp).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700">
                                    {query.blocked_reason 
                                      ? `[Blocked: ${query.blocked_reason}]`
                                      : "[Content filtered by safety guardrails]"}
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="destructive" className="text-xs">
                                      Blocked
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      {query.language}
                                    </Badge>
                                    <Badge className="text-xs bg-red-100 text-red-800">
                                      Risk: {((1 - query.safety_score) * 100).toFixed(0)}%
                                    </Badge>
                                  </div>
                                </div>
                              ))
                            ) : (data.cost_analytics?.interaction_breakdown?.["harmful"] || 0) > 0 ? (
                              Array.from({ length: Math.min(3, data.cost_analytics?.interaction_breakdown?.["harmful"] || 0) }).map((_, index) => (
                                <div key={index} className="bg-white p-2 rounded border text-sm">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="text-xs text-gray-500 font-mono">
                                      session_{String(index + 1).padStart(3, '0')}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                      {new Date().toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p className="text-gray-700">
                                    [Content filtered by safety guardrails]
                                  </p>
                                  <div className="flex gap-1 mt-1">
                                    <Badge variant="destructive" className="text-xs">
                                      Blocked
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                      English
                                    </Badge>
                                  </div>
                                </div>
                              ))
                            ) : (
                              <div className="text-center text-gray-500 py-4">
                                <p className="text-sm">No harmful queries detected</p>
                                <p className="text-xs">Safety guardrails are working effectively</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Interaction Logs */}
                {data.cost_analytics.recent_interactions.length > 0 && (
                  <div className="mt-8">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <BarChart3 className="h-5 w-5" />
                          Interaction Logs
                        </CardTitle>
                        <CardDescription>
                          Most frequent user queries
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b">
                                <th className="text-left p-2 font-medium">
                                  Session ID
                                </th>
                                <th className="text-left p-2 font-medium">
                                  Model
                                </th>
                                <th className="text-left p-2 font-medium">
                                  Query Type
                                </th>
                                <th className="text-left p-2 font-medium">
                                  Language
                                </th>
                                <th className="text-left p-2 font-medium">
                                  Cost
                                </th>
                                <th className="text-left p-2 font-medium">
                                  Time
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {data.cost_analytics.recent_interactions
                                .slice(0, 10)
                                .map((interaction, index) => (
                                  <tr
                                    key={index}
                                    className="border-b hover:bg-gray-50"
                                  >
                                    <td className="p-2">
                                      <div className="text-xs font-mono">
                                        {interaction.session_id?.substring(
                                          0,
                                          8
                                        ) || "N/A"}
                                      </div>
                                    </td>
                                    <td className="p-2">
                                      <Badge
                                        variant="outline"
                                        className="text-xs"
                                      >
                                        {interaction.model.replace("_", " ")}
                                      </Badge>
                                    </td>
                                    <td className="p-2">
                                      <span className="text-xs capitalize">
                                        {interaction.query_type.replace(
                                          "_",
                                          " "
                                        )}
                                      </span>
                                    </td>
                                    <td className="p-2">
                                      <span className="text-xs">
                                        {interaction.language || "Unknown"}
                                      </span>
                                    </td>
                                    <td className="p-2">
                                      <span className="text-xs font-mono">
                                        ${interaction.cost.toFixed(6)}
                                      </span>
                                    </td>
                                    <td className="p-2">
                                      <span className="text-xs text-gray-500">
                                        {new Date(
                                          interaction.timestamp
                                        ).toLocaleDateString()}
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
              </>
            )}
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
