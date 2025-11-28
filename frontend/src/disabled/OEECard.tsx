import { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface OEEData {
  date: string;
  oee: number;
  availability: number;
  performance: number;
  quality: number;
  benchmark: {
    label: string;
    color: string;
    classification: string;
  };
}

interface OEETrendResponse {
  machine_id: string;
  from_date: string;
  to_date: string;
  trend: OEEData[];
}

interface OEECardProps {
  machineId: string;
}

export function OEECard({ machineId }: OEECardProps) {
  const [oeeToday, setOEEToday] = useState<OEEData | null>(null);
  const [oeeTrend, setOEETrend] = useState<OEEData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOEE = async () => {
      try {
        const today = new Date().toISOString().split('T')[0];
        
        // Fetch today's OEE
        const todayResponse = await fetch(
          `http://localhost:8001/v1/machines/${machineId}/oee?date=${today}&shift=daily`
        );
        
        if (todayResponse.ok) {
          const todayData = await todayResponse.json();
          setOEEToday(todayData);
        }

        // Fetch 7-day trend
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const fromDate = sevenDaysAgo.toISOString().split('T')[0];
        
        const trendResponse = await fetch(
          `http://localhost:8001/v1/machines/${machineId}/oee/trend?from_date=${fromDate}&to_date=${today}&shift=daily`
        );
        
        if (trendResponse.ok) {
          const trendData: OEETrendResponse = await trendResponse.json();
          setOEETrend(trendData.trend.reverse()); // Oldest to newest
        }

        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch OEE');
      } finally {
        setLoading(false);
      }
    };

    fetchOEE();
    const interval = setInterval(fetchOEE, 60000); // Refresh every minute

    return () => clearInterval(interval);
  }, [machineId]);

  const getOEEColor = (oee: number): string => {
    if (oee >= 0.85) return '#3b82f6'; // blue (world-class)
    if (oee >= 0.70) return '#10b981'; // green (competitive)
    if (oee >= 0.60) return '#f59e0b'; // yellow (fair)
    return '#ef4444'; // red (unacceptable)
  };

  const downloadCSV = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      const fromDate = thirtyDaysAgo.toISOString().split('T')[0];

      const response = await fetch(
        `http://localhost:8001/v1/machines/${machineId}/oee/export?format=csv&from_date=${fromDate}&to_date=${today}`
      );

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `oee_${machineId}_${fromDate}_${today}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('CSV export failed:', err);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-16 bg-gray-200 rounded mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">OEE</h3>
        <p className="text-red-600">Error: {error}</p>
      </div>
    );
  }

  const chartData = {
    labels: oeeTrend.map(d => {
      const date = new Date(d.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: 'OEE',
        data: oeeTrend.map(d => (d.oee * 100).toFixed(1)),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true,
      },
      {
        label: 'Availability',
        data: oeeTrend.map(d => (d.availability * 100).toFixed(1)),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.05)',
        tension: 0.4,
        fill: false,
        borderDash: [5, 5],
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return `${context.dataset.label}: ${context.parsed.y}%`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: function(value: any) {
            return value + '%';
          }
        }
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">OEE (Overall Equipment Effectiveness)</h3>
        <button
          onClick={downloadCSV}
          className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition"
        >
          📥 Download CSV
        </button>
      </div>

      {oeeToday && (
        <div className="mb-6">
          <div className="flex items-baseline gap-2 mb-2">
            <span
              className="text-4xl font-bold"
              style={{ color: getOEEColor(oeeToday.oee) }}
            >
              {(oeeToday.oee * 100).toFixed(1)}%
            </span>
            <span className="text-sm text-gray-500">Today</span>
            <span
              className="text-xs px-2 py-1 rounded"
              style={{
                backgroundColor: oeeToday.benchmark.color + '20',
                color: oeeToday.benchmark.color
              }}
            >
              {oeeToday.benchmark.label}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Availability</p>
              <p className="text-lg font-semibold text-green-600">
                {(oeeToday.availability * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-gray-500">Performance</p>
              <p className="text-lg font-semibold text-blue-600">
                {(oeeToday.performance * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-gray-500">Quality</p>
              <p className="text-lg font-semibold text-purple-600">
                {(oeeToday.quality * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {oeeTrend.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">7-Day Trend</h4>
          <div style={{ height: '200px' }}>
            <Line data={chartData} options={chartOptions} />
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500">
        <p>OEE = Availability × Performance × Quality</p>
        <div className="flex gap-4 mt-1">
          <span>🔴 &lt;60% Poor</span>
          <span>🟡 60-70% Fair</span>
          <span>🟢 70-85% Good</span>
          <span>🔵 &gt;85% World-Class</span>
        </div>
      </div>
    </div>
  );
}
