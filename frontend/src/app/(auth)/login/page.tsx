export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-6 text-slate-50">
      <form className="w-full max-w-sm space-y-5 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-cyan-300">AVR</p>
          <h1 className="mt-2 text-2xl font-semibold">Đăng nhập</h1>
          <p className="mt-1 text-sm text-slate-400">Xác thực tài khoản sẽ được bổ sung ở task 1-2.</p>
        </div>
        <label className="block space-y-1 text-sm" htmlFor="email">
          <span>Email</span>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 outline-none focus:border-cyan-300"
            id="email"
            name="email"
            placeholder="creator@example.com"
            type="email"
          />
        </label>
        <button
          className="w-full rounded-md bg-cyan-400 px-3 py-2 font-medium text-slate-950 disabled:opacity-60"
          disabled
          type="button"
        >
          Đăng nhập (sắp có)
        </button>
      </form>
    </main>
  );
}
