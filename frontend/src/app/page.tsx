export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-5xl font-bold tracking-tight text-gray-900 dark:text-white">
          Cyber<span className="text-primary-600">Eco</span>
        </h1>
        <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
          A secure platform for bug bounty programs and responsible vulnerability disclosure.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <a
            href="/programs"
            className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
          >
            Explore Programs
          </a>
          <a
            href="/login"
            className="rounded-lg bg-white px-6 py-3 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-white dark:ring-gray-700 dark:hover:bg-gray-700"
          >
            Sign In
          </a>
        </div>
        <p className="mt-12 text-xs text-gray-400">
          Phase 1 — Scaffold Complete
        </p>
      </div>
    </main>
  );
}
