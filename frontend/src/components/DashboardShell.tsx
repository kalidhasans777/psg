import React, { useState } from "react";
import { Bell, LogOut, Menu, X } from "lucide-react";
import { MedoraLogo } from "./MedoraLogo";
import { NotificationItem } from "../types";

export interface NavTab {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface Props {
  roleLabel: string;
  userName: string;
  subtitle?: string;
  bannerImage: string;
  bannerTitle: string;
  bannerSubtitle: string;
  tabs: NavTab[];
  activeTab: string;
  onSelectTab: (id: string) => void;
  onLogout: () => void;
  notifications?: NotificationItem[];
  onMarkNotificationRead?: (id: number) => void;
  children: React.ReactNode;
}

export const DashboardShell: React.FC<Props> = ({
  roleLabel,
  userName,
  subtitle,
  bannerImage,
  bannerTitle,
  bannerSubtitle,
  tabs,
  activeTab,
  onSelectTab,
  onLogout,
  notifications = [],
  onMarkNotificationRead,
  children,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Mobile Sidebar Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-68 bg-[#0B1F3A] text-white flex flex-col transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-5 py-5 border-b border-white/10">
          <MedoraLogo dark size="sm" />
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="rounded-lg p-1 text-slate-300 hover:bg-white/10 lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 py-4 border-b border-white/10">
          <span className="inline-block rounded-full bg-teal-500/20 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-teal-200">
            {roleLabel}
          </span>
          <p className="mt-1.5 font-semibold text-sm truncate">{userName}</p>
          {subtitle && <p className="text-xs text-sky-200 font-mono mt-0.5">{subtitle}</p>}
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {tabs.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  onSelectTab(tab.id);
                  setSidebarOpen(false);
                }}
                className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition cursor-pointer ${
                  active
                    ? "bg-gradient-to-r from-[#0B4F6C] to-[#0D9488] text-white shadow-sm"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                {tab.icon}
                <span className="truncate">{tab.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="p-3 border-t border-white/10">
          <button
            type="button"
            onClick={onLogout}
            className="flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-rose-200 hover:bg-rose-500/20 transition cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-slate-200 bg-white/95 backdrop-blur px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="rounded-xl border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-base sm:text-lg font-bold text-[#0B1F3A]">
                {tabs.find((t) => t.id === activeTab)?.label || roleLabel}
              </h1>
              <p className="text-xs text-slate-500 hidden sm:block">
                MEDORA – One Patient. One Permanent ID. A Complete Medical Journey.
              </p>
            </div>
          </div>

          <div className="relative flex items-center gap-3">
            <button
              type="button"
              onClick={() => setNotifOpen((p) => !p)}
              className="relative rounded-xl border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50 cursor-pointer"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-teal-600 text-[10px] font-bold text-white">
                  {unreadCount}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 top-12 z-50 w-80 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#0B4F6C]">Notifications</span>
                  <button type="button" onClick={() => setNotifOpen(false)} className="text-xs text-slate-400">
                    Close
                  </button>
                </div>
                {notifications.length === 0 ? (
                  <p className="py-4 text-center text-xs text-slate-500">No notifications yet.</p>
                ) : (
                  <div className="max-h-72 overflow-y-auto space-y-2">
                    {notifications.slice(0, 8).map((n) => (
                      <div
                        key={n.id}
                        onClick={() => onMarkNotificationRead?.(n.id)}
                        className={`rounded-xl p-2.5 text-xs cursor-pointer ${
                          n.is_read ? "bg-slate-50 text-slate-600" : "bg-teal-50/70 border border-teal-100 text-slate-800"
                        }`}
                      >
                        <p className="font-semibold">{n.title}</p>
                        <p className="mt-0.5 text-[11px]">{n.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 max-w-7xl w-full mx-auto space-y-6">
          {/* Healthcare Visual Banner */}
          <div className="no-print relative overflow-hidden rounded-2xl h-36 sm:h-40 shadow-sm">
            <img
              src={bannerImage}
              alt={bannerTitle}
              className="h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#0B1F3A]/90 via-[#0B4F6C]/80 to-teal-700/65 flex flex-col justify-center px-6 text-white">
              <p className="text-xs font-semibold uppercase tracking-widest text-teal-200">{roleLabel}</p>
              <h2 className="mt-1 text-xl sm:text-2xl font-bold">{bannerTitle}</h2>
              <p className="mt-1 text-xs sm:text-sm text-sky-100 max-w-2xl">{bannerSubtitle}</p>
            </div>
          </div>

          {children}
        </main>
      </div>
    </div>
  );
};
