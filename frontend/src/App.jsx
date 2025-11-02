import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

// --- Chart Configuration ---
const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      labels: {
        color: '#ffffff', // Legend text color
        font: {
          size: 14
        }
      }
    },
    title: {
      display: true,
      text: 'Productivity Summary by User',
      color: '#ffffff', // Title text color
      font: {
        size: 18
      }
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        color: '#dddddd', // Y-axis labels
        stepSize: 1
      },
      grid: {
        color: '#555555' // Y-axis grid lines
      }
    },
    x: {
      ticks: {
        color: '#dddddd' // X-axis labels
      },
      grid: {
        color: '#555555' // X-axis grid lines
      }
    }
  }
};

// --- Main App Component ---
function App() {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // --- Data Fetching Logic ---
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        // We use /api/... because Nginx is proxying this
        const response = await fetch('/api/metrics/summary');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        console.log("Fetched data:", data);

        // --- NEW DATA PROCESSING ---
        // The API now returns aggregated data, so this is much simpler!
        
        const labels = data.map(item => item.user_id);
        
        setChartData({
          labels: labels,
          datasets: [
            {
              label: 'Total Events',
              data: data.map(item => item.total_events),
              backgroundColor: 'rgba(138, 123, 226, 0.7)',
              borderColor: 'rgba(138, 123, 226, 1)',
              borderWidth: 1,
            },
            {
              label: 'Tasks Created',
              data: data.map(item => item.total_tasks_created),
              backgroundColor: 'rgba(54, 162, 235, 0.7)',
              borderColor: 'rgba(54, 162, 235, 1)',
              borderWidth: 1,
            },
            {
              label: 'Tasks Completed',
              data: data.map(item => item.total_tasks_completed),
              backgroundColor: 'rgba(75, 192, 192, 0.7)',
              borderColor: 'rgba(75, 192, 192, 1)',
              borderWidth: 1,
            }
          ],
        });
        
      } catch (e) {
        console.error("Failed to fetch data:", e);
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // --- Render Logic ---
  const renderContent = () => {
    if (loading) {
      return <p className="text-center text-lg">Loading data...</p>;
    }
    if (error) {
      return <p className="text-center text-lg text-red-400">Error: {error}</p>;
    }
    if (chartData.labels.length === 0) {
      return <p className="text-center text-lg">No data available. Send some events!</p>;
    }
    return (
      <div className="relative" style={{ height: '450px' }}>
        <Bar options={options} data={chartData} />
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-8">
      <header className="text-center mb-8">
        <h1 className="text-4xl font-bold text-indigo-400">PulseBoard Dashboard</h1>
        <p className="text-lg text-gray-400">Real-time team productivity analytics</p>
      </header>
      <main>
        <div className="bg-gray-800 shadow-xl rounded-lg p-4 sm:p-6 max-w-4xl mx-auto">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

export default App;

