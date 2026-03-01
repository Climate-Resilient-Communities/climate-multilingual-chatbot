import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-green-50 to-white px-4 text-center">
      <h1 className="mb-2 text-6xl font-bold text-green-800">404</h1>
      <p className="mb-6 text-lg text-gray-600">Page not found</p>
      <Link
        href="/"
        className="rounded-lg bg-green-700 px-6 py-3 text-white transition-colors hover:bg-green-800"
      >
        Back to Chat
      </Link>
    </div>
  );
}
