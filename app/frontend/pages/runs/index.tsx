import { useSession, signIn } from 'next-auth/react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import Link from 'next/link';

// Fetch the list of runs from the API
async function fetchRuns() {
  const response = await axios.get('/api/runs');
  return response.data;
}

export default function RunsPage() {
  const { data: session, status } = useSession();
  // Only fetch runs when the user is authenticated
  const {
    data: runs,
    isLoading,
    isError,
  } = useQuery(['runs'], fetchRuns, {
    enabled: status === 'authenticated',
  });

  if (status === 'loading') {
    return <div className="p-4">Loading session…</div>;
  }

  if (status === 'unauthenticated' || !session) {
    return (
      <div className="p-4">
        <p className="mb-2">You must be signed in to view run history.</p>
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
    return <div className="p-4">Loading runs…</div>;
  }

  if (isError) {
    return <div className="p-4 text-red-500">Error loading runs.</div>;
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Run History</h1>
      {Array.isArray(runs) && runs.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white shadow-md rounded-lg overflow-hidden">
            <thead className="bg-gray-100">
              <tr>
                <th className="py-2 px-4 text-left">Run ID</th>
                <th className="py-2 px-4 text-left">Model Version ID</th>
                <th className="py-2 px-4 text-left">Solver</th>
                <th className="py-2 px-4 text-left">Status</th>
                <th className="py-2 px-4 text-left">Objective</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run: any) => (
                <tr key={run.id} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-4">
                    <Link href={`/runs/${run.id}`} className="text-blue-600 hover:underline">
                      {run.id}
                    </Link>
                  </td>
                  <td className="py-2 px-4">{run.model_version_id}</td>
                  <td className="py-2 px-4">{run.solver}</td>
                  <td className="py-2 px-4 capitalize">{run.status}</td>
                  <td className="py-2 px-4">{run.objective_value ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No runs found.</p>
      )}
    </div>
  );
}
