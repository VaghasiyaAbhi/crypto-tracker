'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { TrendingUp, Bell, User, LogOut, Award, Settings } from 'lucide-react';
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuItem } from '@/components/ui/dropdown-menu';
import { useEffect, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { getUser, logout, authenticatedFetch } from '@/lib/auth';

interface User {
  first_name: string;
  last_name: string;
  email: string;
  mobile_number: string;
  username: string;
  subscription_plan: 'free' | 'basic' | 'enterprise';
  is_premium_user: boolean;
}

const Header = () => {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  const handleLogout = useCallback(() => {
    logout();
  }, []);

  const fetchUserDetails = useCallback(async () => {
    // Check authentication using centralized auth utility
    const authUser = getUser();
    if (!authUser) {
      // User not authenticated, don't logout (let page handle it)
      return;
    }

    try {
      const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/`);

      if (!response) {
        // authenticatedFetch handles logout on auth errors
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch user details');
      }

      const data = await response.json();
      setUser(data);
    } catch (err) {
      console.error('Error fetching user details in header:', err);
    }
  }, []);

  useEffect(() => {
    fetchUserDetails();
  }, [fetchUserDetails]);

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between bg-white shadow-sm p-2 rounded-xl mb-4">
      <div className="flex items-center space-x-2">
  <span className="text-lg font-bold">Volume Tracker</span>
        <Button variant="ghost" asChild>
          <Link href="/dashboard">
            <TrendingUp className="h-4 w-4 mr-1" />
            Live
          </Link>
        </Button>
        <Button variant="ghost" asChild>
          <Link href="/alerts">
            <Bell className="h-4 w-4 mr-1" />
            Alerts
          </Link>
        </Button>
      </div>
      <div className="flex items-center space-x-2">
        <div className="text-sm text-gray-500 flex items-center space-x-2">
            <Button
              variant="ghost"
              onClick={() => router.push('/plan-management')}
              className={cn(
                'font-semibold px-3 py-1 h-auto hover:bg-gray-100',
                user?.subscription_plan === 'enterprise' ? 'text-green-600 hover:text-green-700' :
                user?.subscription_plan === 'basic' ? 'text-blue-600 hover:text-blue-700' :
                    'text-gray-600 hover:text-gray-700'
              )}
            >
              {user?.subscription_plan ? user.subscription_plan.charAt(0).toUpperCase() + user.subscription_plan.slice(1) : ''} Plan
            </Button>
            {user?.subscription_plan === 'free' && (
                <Button
                    onClick={() => router.push('/upgrade-plan')}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl"
                    size="sm"
                >
                    UPGRADE
                </Button>
            )}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="rounded-full size-9 p-0">
              <User className="h-7 w-7" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>
              <div className="font-semibold">{user?.first_name} {user?.last_name}</div>
              <div className="text-sm text-gray-500">{user?.email}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings">
                <Settings className="h-4 w-4 mr-2" />
                <span>Settings</span>
              </Link>
            </DropdownMenuItem>
            {!user?.is_premium_user && (
              <DropdownMenuItem asChild>
                <Link href="/upgrade-plan">
                  <Award className="h-4 w-4 mr-2" />
                  <span>Upgrade Plan</span>
                </Link>
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-red-500 focus:text-red-500">
              <LogOut className="h-4 w-4 mr-2" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};

export default Header;