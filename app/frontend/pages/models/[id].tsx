import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import dynamic from 'next/dynamic';
import { useState } from 'react';
import { useSession, signIn } from 'next-auth/react';

// Monaco editor is dynamically imported to avoid SSR issues
const MonacoEditor = dynamic(
  () => import('@monaco-editor/react').then((m) => m.default),
  { ssr: false }
);

export default function ModelEditorPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const { id } = router.query;

  const { data: model, isLoading, error } = useQuery({
    queryKey: ['model', id],
    queryFn: async () => {
      if (!id) return null;
      const res = await axios.get(`/api/models/${id}`);
      return res.data;
    },
    enabled: !!id && status === 'authenticated',
  });

  const [modelJson, setModelJson] = useState<string>('{}');

  if (status === 'loading') return <p>Loading session...</p>;
  if (!session)
    return (
      <div className="p-4">
        <p>You must be signed in to edit a model.</p>
        <button
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded"
          onClick={() => signIn()}
        >
          Sign in
        </button>
      </div>
    );
  if (isLoading) return <p>Loading model...</p>;
  if (error) return <p>Error loading model</p>;

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Edit Model {id}</h1>
      <div className="mb-4">
        <MonacoEditor
          height="400px"
          defaultLanguage="json"
          defaultValue={JSON.stringify(model?.definition_json ?? {}, null, 2)}
          onChange={(value) => setModelJson(value ?? '')}
          options={{ automaticLayout: true }}
        />
      </div>
      <button
        className="px-4 py-2 bg-green-600 text-white rounded"
        onClick={() => {
          // TODO: Submit updated model JSON to API
          console.log('Updated model JSON:', modelJson);
        }}
      >
        Save Changes
      </button>
    </div>
  );
}
