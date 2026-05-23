import Sidebar from '@/components/Sidebar';
import FinancialsClient from './FinancialsClient';

export default function FinancialsPage() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <FinancialsClient />
      </main>
    </div>
  );
}
