import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, Activity } from 'lucide-react';
import clsx from 'clsx';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  const navItems = [
    { name: '仪表盘', path: '/dashboard', icon: LayoutDashboard },
    { name: '线索情报', path: '/dashboard/clues', icon: Activity },
    { name: '当前画像', path: '/dashboard/persona', icon: FileText },
    { name: '任务配置', path: '/dashboard/settings', icon: Settings },
  ];

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <h1 className="logo-text">Easyget</h1>
      </div>
      
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/dashboard'} // Dashboard 主页完全匹配
              className={({ isActive }) => 
                clsx('nav-link', { 'nav-link-active': isActive })
              }
            >
              <Icon size={18} className="nav-icon" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>
      
      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="avatar">A</div>
          <div className="user-info">
            <span className="user-name">Admin</span>
            <span className="user-role">Free Plan</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
