import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useSession, signIn } from 'next-auth/react';

export default function Dashboard() {
  const { data: session, status } = useSession();

  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await axios.get('/api/projects');
      return res.data;
    },
    enabled: status === 'authenticated',
  });

  if (status === 'loading') return <p>Loading session...</p>;
  if (!session) {
    return (
      <div className="p-4">
        <p>You must be signed in to view the dashboard.</p>
        <button
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded"
          onClick={() => signIn()}
        >
          Sign in
        </button>
      </div>
    );
  }

  if (isLoading) return <p>Loading projects...</p>;
  if (error) return <p>Error loading projects</p>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Projects</h1>
      <ul className="space-y-2">
        {(projects || []).map((project: any) => (
          <li key={project.id} className="border p-2 rounded">
            {project.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
