import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { createPageUrl } from './utils';
import { 
  LayoutDashboard, 
  CheckSquare, 
  Brain, 
  DollarSign, 
  FolderKanban, 
  Users,
  Menu,
  X
} from 'lucide-react';

export default function Layout({ children, currentPageName }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { name: 'ControlHall', label: 'Control Hall', icon: LayoutDashboard },
    { name: 'Tasks', label: 'Tasks', icon: CheckSquare },
    { name: 'AICore', label: 'AI Core', icon: Brain },
    { name: 'Deals', label: 'Deals', icon: DollarSign },
    { name: 'Projects', label: 'Projects', icon: FolderKanban },
    { name: 'Agents', label: 'Agents', icon: Users }
  ];

  return (
    <div className="app-layout">
      <style>{`
        .app-layout {
          display: flex;
          min-height: 100vh;
          background: radial-gradient(circle at top, #0A241D 0%, #020B09 55%, #000000 100%);
          color: #DDEAE5;
        }

        .sidebar {
          width: 240px;
          background: 
            linear-gradient(135deg, rgba(10,36,29,0.95), rgba(2,11,9,0.98)),
            radial-gradient(circle at 50% 0%, rgba(47,224,161,0.1), transparent 60%);
          border-right: 1px solid rgba(47,224,161,0.3);
          padding: 24px 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          position: fixed;
          height: 100vh;
          z-index: 100;
          backdrop-filter: blur(20px);
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 4px 0 40px rgba(0,0,0,0.5), inset -1px 0 20px rgba(47,224,161,0.1);
        }

        .sidebar::before {
          content: "";
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            90deg,
            transparent 0,
            rgba(47,224,161,0.02) 1px,
            transparent 2px,
            transparent 20px
          );
          pointer-events: none;
          animation: sidebarScan 3s linear infinite;
        }

        @keyframes sidebarScan {
          0% { transform: translateY(-20px); }
          100% { transform: translateY(20px); }
        }

        .sidebar-logo {
          font-size: 18px;
          font-weight: 700;
          color: #2FE0A1;
          margin-bottom: 24px;
          padding: 0 12px;
          text-shadow: 0 0 20px rgba(47,224,161,0.6);
          animation: logoPulse 3s ease-in-out infinite;
          letter-spacing: 1px;
        }

        @keyframes logoPulse {
          0%, 100% { 
            text-shadow: 0 0 20px rgba(47,224,161,0.6);
            transform: scale(1);
          }
          50% { 
            text-shadow: 0 0 30px rgba(47,224,161,0.9);
            transform: scale(1.02);
          }
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          border-radius: 10px;
          text-decoration: none;
          color: #9CB7AA;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          font-size: 14px;
          font-weight: 500;
          position: relative;
          overflow: hidden;
        }

        .nav-item::before {
          content: "";
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 3px;
          background: linear-gradient(to bottom, #2FE0A1, #3BF2BD);
          transform: scaleY(0);
          transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 0 10px rgba(47,224,161,0.6);
        }

        .nav-item::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(90deg, rgba(47,224,161,0.1), transparent);
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .nav-item:hover {
          background: rgba(47,224,161,0.1);
          color: #DDEAE5;
          transform: translateX(6px) scale(1.02);
          box-shadow: 0 4px 16px rgba(47,224,161,0.15);
        }

        .nav-item:hover::after {
          opacity: 1;
        }

        .nav-item.active {
          background: rgba(47,224,161,0.15);
          color: #2FE0A1;
          box-shadow: 0 0 20px rgba(47,224,161,0.3);
          font-weight: 600;
        }

        .nav-item.active::before {
          transform: scaleY(1);
          animation: glowPulse 2s ease-in-out infinite;
        }

        @keyframes glowPulse {
          0%, 100% { box-shadow: 0 0 10px rgba(47,224,161,0.6); }
          50% { box-shadow: 0 0 20px rgba(47,224,161,1); }
        }

        .main-content {
          margin-left: 240px;
          flex: 1;
          min-height: 100vh;
        }

        .mobile-menu-button {
          display: none;
          position: fixed;
          top: 20px;
          left: 20px;
          z-index: 200;
          background: rgba(12,36,30,0.95);
          border: 1px solid rgba(47,224,161,0.5);
          border-radius: 10px;
          padding: 10px;
          color: #2FE0A1;
          cursor: pointer;
          backdrop-filter: blur(10px);
        }

        @media (max-width: 1024px) {
          .sidebar {
            transform: translateX(-100%);
            box-shadow: 8px 0 60px rgba(0,0,0,0.8);
          }

          .sidebar.mobile-open {
            transform: translateX(0);
            animation: slideInLeft 0.4s cubic-bezier(0.4, 0, 0.2, 1);
          }

          @keyframes slideInLeft {
            from { 
              transform: translateX(-100%);
              opacity: 0.8;
            }
            to { 
              transform: translateX(0);
              opacity: 1;
            }
          }

          .main-content {
            margin-left: 0;
          }

          .mobile-menu-button {
            display: block;
          }
        }

        .sidebar-overlay {
          display: none;
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.7);
          z-index: 90;
          backdrop-filter: blur(4px);
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .sidebar-overlay.active {
          display: block;
          animation: fadeIn 0.3s ease forwards;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>

      <button 
        className="mobile-menu-button"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
      >
        {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <div 
        className={`sidebar-overlay ${mobileMenuOpen ? 'active' : ''}`}
        onClick={() => setMobileMenuOpen(false)}
      />

      <nav className={`sidebar ${mobileMenuOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-logo">AI CRM CONTROL</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              to={createPageUrl(item.name)}
              className={`nav-item ${currentPageName === item.name ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}