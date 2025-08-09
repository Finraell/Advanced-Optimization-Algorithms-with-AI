import { signIn, signOut, useSession } from 'next-auth/react';
import Link from 'next/link';

export default function Home() {
  const { data: session, status } = useSession();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 space-y-4">
      <h1 className="text-3xl font-bold">Advanced Optimization Algorithms with AI</h1>
      <p className="text-lg text-center max-w-2xl">
        A secure, scalable platform for building and solving optimisation problems.  Use the
        AI copilot to translate natural language into models, run solvers and view results.
      </p>
      {status === 'loading' ? (
        <p>Checking authentication…</p>
      ) : session ? (
        <>
          <p>Signed in as {session.user?.email}</p>
          <div className="space-x-4">
            <Link href="/dashboard" className="px-4 py-2 bg-blue-600 text-white rounded">
              Go to Dashboard
            </Link>
            <button
              onClick={() => signOut()}
              className="px-4 py-2 bg-gray-600 text-white rounded"
            >
              Sign out
            </button>
          </div>
        </>
      ) : (
        <button
          onClick={() => signIn()}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Sign in
        </button>
      )}
    </main>
  );
}
