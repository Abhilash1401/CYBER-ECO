'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function CompanyDashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const navItems = [
    { name: 'Organization', href: '/dashboard/company' },
    { name: 'Team', href: '/dashboard/company/members' },
    { name: 'Programs', href: '/dashboard/company/programs' },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-4 text-xl font-bold border-b border-gray-800">CyberEco</div>
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-4 py-2 rounded-md ${
                pathname === item.href || (item.href !== '/dashboard/company' && pathname?.startsWith(item.href))
                  ? 'bg-blue-600'
                  : 'hover:bg-gray-800'
              }`}
            >
              {item.name}
            </Link>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white shadow-sm p-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800">Company Dashboard</h1>
          <div className="text-gray-600">Admin</div>
        </header>
        <main className="flex-1 overflow-auto p-6 text-black">
          {children}
        </main>
      </div>
    </div>
  );
}
