import Link from "next/link";

export default function Home() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-6 text-slate-50">
      <section className="max-w-lg space-y-5 text-center">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300">AVR</p>
        <h1 className="text-4xl font-semibold tracking-tight">AI Video Production Studio</h1>
        <p className="text-slate-300">
          Research, kiểm chứng nội dung và render video social bằng Remotion.
        </p>
        <Link
          className="inline-flex rounded-md bg-cyan-400 px-4 py-2 font-medium text-slate-950 hover:bg-cyan-300"
          href="/login"
        >
          Đăng nhập
        </Link>
      </section>
    </main>
  );
}
