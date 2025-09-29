"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BarChart3 } from "lucide-react";

interface AdminDashboardModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AdminDashboardModal({
  open,
  onOpenChange,
}: AdminDashboardModalProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleAuth = async () => {
    if (!password.trim()) {
      setError("Please enter a password");
      return;
    }

    try {
      // Verify password with backend API
      const response = await fetch('/api/v1/admin/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${password}`
        }
      });

      if (response.ok) {
        setIsAuthenticated(true);
        setError(null);
      } else {
        setError("Invalid admin credentials");
      }
    } catch (error) {
      console.error('Authentication error:', error);
      setError("Authentication failed. Please try again.");
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleAuth();
    }
  };

  const resetState = () => {
    console.log("Resetting state");
    setIsAuthenticated(false);
    setPassword("");
    setError(null);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      resetState();
    }
    onOpenChange(newOpen);
  };

  if (!isAuthenticated) {
    return (
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Admin Dashboard Access</DialogTitle>
            <DialogDescription>
              Enter the admin password to view analytics dashboard
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Input
                type="password"
                placeholder="Admin password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyPress={handleKeyPress}
              />
              {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
            </div>
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleAuth}>Access Dashboard</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            MLCC Feedback Dashboard
          </DialogTitle>
          <DialogDescription>
            Admin dashboard for monitoring chatbot feedback and analytics
          </DialogDescription>
        </DialogHeader>

        <div className="py-8 text-center">
          <div className="text-4xl font-bold text-green-600 mb-4">
            MLCC Feedback Dashboard
          </div>
          <p className="text-lg text-muted-foreground">
            Welcome to the Multi-Lingual Climate Chatbot admin panel.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            This dashboard provides insights into user feedback and chatbot
            performance.
          </p>
        </div>

        <div className="flex justify-end">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Close Dashboard
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
