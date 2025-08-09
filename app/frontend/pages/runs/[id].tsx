import { useRouter } from 'next/router';
import { useSession, signIn } from 'next-auth/react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface RunDetail {
  id: string;
  model_version_id: string;
  solver: string;
  status: string;
  objective_value: number | null;
  logs?: any;
}

// Fetch a specific run by ID
async function fetchRun(id: string): Promise<RunDetail> {
  const response = await axios.get(`/api/runs/${id}`);
  return response.data;
}

export default function RunDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const { data: session, status: sessionStatus } = useSession();

  const {
    data: run,
    isLoading,
    isError,
  } = useQuery(["run", id], () => fetchRun(id as string), {
    enabled: sessionStatus === 'authenticated' && typeof id === 'string',
  });

  if (sessionStatus === 'loading') {
    return <div className="p-4">Loading session…</div>;
  }

  if (sessionStatus === 'unauthenticated' || !session) {
    return (
      <div className="p-4">
        <p className="mb-2">You must be signed in to view run details.</p>
        <button
          className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
          onClick={() => signIn()}
        >
          Sign In
        </button>
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-4">Loading run…</div>;
  }

  if (isError || !run) {
    return <div className="p-4 text-red-500">Error loading run.</div>;
  }

  // Generate a dummy chart dataset based on objective value. If objective_value exists,
  // create a synthetic trend; otherwise just show flat line.
  const chartData = Array.from({ length: 10 }, (_, index) => {
    const x = index + 1;
    const y = run.objective_value != null ? (run.objective_value * (1 + (10 - x) / 100)) : 0;
    return { step: x, objective: y };
  });

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Run Details: {run.id}</h1>
      <div className="mb-4">
        <p><strong>Model Version ID:</strong> {run.model_version_id}</p>
        <p><strong>Solver:</strong> {run.solver}</p>
        <p><strong>Status:</strong> {run.status}</p>
        <p><strong>Objective:</strong> {run.objective_value ?? '—'}</p>
      </div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold mb-2">Objective Trend (simulated)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="step" label={{ value: 'Step', position: 'insideBottomRight', offset: -5 }} />
            <YAxis dataKey="objective" label={{ value: 'Objective', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Line type="monotone" dataKey="objective" stroke="#8884d8" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
