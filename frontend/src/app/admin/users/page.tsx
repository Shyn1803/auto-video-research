"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api/interceptor";
import { useAuth } from "@/lib/auth/AuthProvider";

type FormState = "default" | "loading" | "error";
type Role = "admin" | "creator";

interface UserRow {
	id: string;
	email: string;
	display_name: string;
	role: Role;
	is_active: boolean;
	must_change_password: boolean;
	created_at: string;
	updated_at: string;
}

type ViewState = "default" | "loading" | "error" | "empty";

export default function AdminUsersPage() {
	const [users, setUsers] = useState<UserRow[]>([]);
	const [total, setTotal] = useState(0);
	const [view, setView] = useState<ViewState>("default");
	const [errorMsg, setErrorMsg] = useState("");
	const [page, setPage] = useState(1);
	const pageSize = 20;

	// create dialog
	const [openCreate, setOpenCreate] = useState(false);
	const [createForm, setCreateForm] = useState({
		email: "", display_name: "", password: "", role: "creator" as Role,
	});
	const [createState, setCreateState] = useState<FormState>("default");
	const [createErr, setCreateErr] = useState("");
	const [lockConfirm, setLockConfirm] = useState<string | null>(null);
	const [lockState, setLockState] = useState<FormState>("default");
	const [lockErr, setLockErr] = useState("");

	const { accessToken } = useAuth();
	const currentUserId = useMemo(() => {
		try {
			const token = accessToken;
			if (!token) return null;
			const payload = JSON.parse(atob(token.split(".")[1]));
			return payload.sub;
		} catch {
			return null;
		}
	}, [accessToken]);

	const isSelf = useCallback(
		(uid: string) => uid === currentUserId,
		[currentUserId],
	);

	// ------------------------------------------------------------------
	// load list
	// ------------------------------------------------------------------

	const loadUsers = useCallback(async (p: number) => {
		setView("loading");
		try {
			const { data } = await api.get<{
				items: UserRow[];
				total: number;
				page: number;
				size: number;
			}>("/users", { params: { page: p, size: pageSize } });
			setUsers(data.items);
			setTotal(data.total);
			setView(data.items.length === 0 ? "empty" : "default");
		} catch (err: unknown) {
			setView("error");
			const e = err as { response?: { data?: { detail?: string } } };
			setErrorMsg(e?.response?.data?.detail ?? "Không tải được danh sách người dùng");
		}
	}, [pageSize]);

	useEffect(() => {
		loadUsers(page);
		// eslint-disable-next-line react-hooks/exhaustive-deps --
	}, [loadUsers, page]);

	// ------------------------------------------------------------------
	// create user
	// ------------------------------------------------------------------

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		setCreateErr("");
		setCreateState("loading");
		try {
			await api.post("/users", {
				email: createForm.email.trim(),
				display_name: createForm.display_name.trim(),
				role: createForm.role,
				password: createForm.password,
			});
			setOpenCreate(false);
			setCreateForm({ email: "", display_name: "", password: "", role: "creator" });
			await loadUsers(1);
		} catch (err: unknown) {
			const e = err as { response?: { data?: { detail?: string } } };
			setCreateErr(e?.response?.data?.detail ?? "Lỗi tạo người dùng");
			setCreateState("error");
		} finally {
			setCreateState((s) => (s === "loading" ? "default" : s));
		}
	};

	// ------------------------------------------------------------------
	// lock / unlock
	// ------------------------------------------------------------------

	const handleLock = async (id: string) => {
		setLockErr("");
		setLockState("loading");
		try {
			await api.post(`/users/${id}/lock`);
			setLockConfirm(null);
			await loadUsers(page);
		} catch (err: unknown) {
			const e = err as { response?: { data?: { detail?: string } } };
			setLockErr(e?.response?.data?.detail ?? "Lỗi khóa tài khoản");
			setLockState("error");
		} finally {
			setLockState((s) => (s === "loading" ? "default" : s));
		}
	};

	const handleUnlock = async (id: string) => {
		try {
			await api.post(`/users/${id}/unlock`);
			await loadUsers(page);
		} catch (err: unknown) {
			const e = err as { response?: { data?: { detail?: string } } };
			window.alert(e?.response?.data?.detail ?? "Không thể mở khóa");
		}
	};

	const handleRoleChange = async (id: string, newRole: Role) => {
		try {
			await api.patch(`/users/${id}`, { role: newRole });
			await loadUsers(page);
		} catch (err: unknown) {
			const e = err as { response?: { data?: { detail?: string } } };
			window.alert(e?.response?.data?.detail ?? "Không thể đổi vai trò");
		}
	};

	// ------------------------------------------------------------------
	// render
	// ------------------------------------------------------------------

	const totalPages = Math.max(1, Math.ceil(total / pageSize));

	return (
		<section className="mx-auto max-w-5xl space-y-6 p-6">
			<header className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-semibold text-slate-50">
						Quản trị viên
					</h1>
					<p className="text-sm text-slate-400">
						Quản lý người dùng — vai trò, khóa/mở khóa.
					</p>
				</div>
				<button
					type="button"
					onClick={() => setOpenCreate(true)}
					className="rounded-md bg-cyan-400 px-4 py-2 font-medium text-slate-950 hover:bg-cyan-300"
				>
					+ Thêm người dùng
				</button>
			</header>

			{/* -- table -------------------------------------------------------- */}
			<div className="overflow-x-auto rounded-xl border border-slate-800">
				<table className="w-full text-left text-sm" caption="Danh sách người dùng">
					<thead>
						<tr className="border-b border-slate-800 text-slate-400">
							<th className="px-4 py-3">Email</th>
							<th className="px-4 py-3">Tên</th>
							<th className="px-4 py-3">Vai trò</th>
							<th className="px-4 py-3">Trạng thái</th>
							<th className="px-4 py-3">Tạo lúc</th>
							<th className="px-4 py-3">Bắt buộc đổi MK</th>
							<th className="px-4 py-3 text-right">Hành động</th>
						</tr>
					</thead>
					<tbody>
						{view === "loading" && (
							<tr>
								<td colSpan={7} className="px-4 py-12 text-center text-slate-500">
									Đang tải…
								</td>
							</tr>
						)}
						{view === "error" && (
							<tr>
								<td colSpan={7} className="px-4 py-12 text-center text-red-400">
									{errorMsg}
								</td>
							</tr>
						)}
						{view === "empty" && (
							<tr>
								<td colSpan={7} className="px-4 py-12 text-center text-slate-500">
									Chưa có người dùng nào. Nhấn &quot;Thêm người dùng&quot; để tạo tài
									khoản đầu tiên.
								</td>
							</tr>
						)}
						{users.map((u) => {
							const self = isSelf(u.id);
							return (
								<tr key={u.id} className="border-b border-slate-800/60 hover:bg-slate-900/40">
									<td className="px-4 py-3 text-slate-200">{u.email}</td>
									<td className="px-4 py-3">{u.display_name}</td>
									<td className="px-4 py-3">
										<select
											aria-label="Vai trò"
											value={u.role}
											disabled={self}
											className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
											onChange={(e) => {
												const v = e.target.value as Role;
												if (!self) handleRoleChange(u.id, v);
											}}
										>
											<option value="admin">Admin</option>
											<option value="creator">Creator</option>
										</select>
										{self && (
											<span className="ml-2 text-xs text-slate-500" title="Không thể đổi vai trò chính mình">
												🔒
											</span>
										)}
									</td>
									<td className="px-4 py-3">
										{u.is_active ? (
											<span className="text-emerald-400">Active</span>
										) : (
											<span className="text-red-400">Locked</span>
										)}
									</td>
									<td className="px-4 py-3 text-slate-400">
										{new Date(u.created_at).toLocaleDateString("vi-VN")}
									</td>
									<td className="px-4 py-3">
										{u.must_change_password ? "Có" : "Không"}
									</td>
									<td className="px-4 py-3 text-right">
										{u.is_active ? (
											<>
												<button
													type="button"
													disabled={self}
													onClick={() => setLockConfirm(u.id)}
													title={self ? "Không thể khóa chính mình" : "Khóa người dùng"}
													className="mr-2 rounded-md border border-slate-700 px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-40 hover:border-red-500 hover:text-red-400"
												>
													Khóa
												</button>
											</>
										) : (
											<button
												type="button"
												onClick={() => handleUnlock(u.id)}
												className="rounded-md border border-slate-700 px-2 py-1 text-sm hover:border-emerald-500 hover:text-emerald-400"
											>
												Mở khóa
											</button>
										)}
									</td>
								</tr>
							);
						})}
					</tbody>
				</table>
			</div>

			{/* -- pagination ---------------------------------------------------- */}
			{view === "default" && (
				<nav className="flex items-center justify-between" aria-label="Phân trang">
					<button
						type="button"
						disabled={page <= 1}
						onClick={() => { setPage((p) => p - 1); }}
						className="rounded-md border border-slate-700 px-3 py-1 disabled:opacity-40"
					>
						Trước
					</button>
					<span className="text-sm text-slate-400">
						Trang {page}/{totalPages} ({total} người dùng)
					</span>
					<button
						type="button"
						disabled={page >= totalPages}
						onClick={() => { setPage((p) => p + 1); }}
						className="rounded-md border border-slate-700 px-3 py-1 disabled:opacity-40"
					>
						Sau
					</button>
				</nav>
			)}

			{/* -- create dialog ------------------------------------------------ */}
			{openCreate && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
					role="dialog"
					aria-modal="true"
					aria-label="Tạo người dùng mới"
				>
					<form
						onSubmit={handleCreate}
						className="w-full max-w-md space-y-4 rounded-xl border border-slate-700 bg-slate-900 p-6"
					>
						<h2 className="text-lg font-semibold">Tạo người dùng mới</h2>
						<label className="block space-y-1 text-sm">
							<span className="text-slate-300">Email</span>
							<input
								type="email"
								aria-label="Email"
								required
								className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50"
								value={createForm.email}
								onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
							/>
						</label>
						<label className="block space-y-1 text-sm">
							<span className="text-slate-300">Tên hiển thị</span>
							<input
								aria-label="Tên hiển thị"
								required
								className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50"
								value={createForm.display_name}
								onChange={(e) => setCreateForm((f) => ({ ...f, display_name: e.target.value }))}
							/>
						</label>
						<label className="block space-y-1 text-sm">
							<span className="text-slate-300">Mật khẩu tạm</span>
							<input
								type="password"
								aria-label="Mật khẩu tạm"
								required
								minLength={10}
								className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50"
								value={createForm.password}
								onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
							/>
						</label>
						<label className="block space-y-1 text-sm">
							<span className="text-slate-300">Vai trò</span>
							<select
								aria-label="Vai trò"
								className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-50"
								value={createForm.role}
								onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value as Role }))}
							>
								<option value="creator">Creator</option>
								<option value="admin">Admin</option>
							</select>
						</label>
						{createErr && (
							<p className="text-sm text-red-400" role="alert">{createErr}</p>
						)}
						<div className="flex justify-end gap-3 pt-2">
							<button
								type="button"
								onClick={() => setOpenCreate(false)}
								className="rounded-md border border-slate-700 px-4 py-2"
							>
								Hủy
							</button>
							<button
								type="submit"
								disabled={createState === "loading"}
								className="rounded-md bg-cyan-400 px-4 py-2 font-medium text-slate-950 disabled:opacity-50"
							>
								{createState === "loading" ? "Đang tạo…" : "Tạo"}
							</button>
						</div>
					</form>
				</div>
			)}

			{/* -- lock confirmation dialog ------------------------------------- */}
			{lockConfirm && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
					role="alertdialog"
					aria-modal="true"
					aria-label="Xác nhận khóa"
				>
					<div className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-6 space-y-4">
						<h3 className="text-lg font-semibold">Xác nhận khóa người dùng</h3>
						<p className="text-sm text-slate-300">
							Phiên đăng nhập của người này sẽ bị hủy ngay lập tức.
						</p>
						{lockErr && (
							<p className="text-sm text-red-400" role="alert">{lockErr}</p>
						)}
						<div className="flex justify-end gap-3">
							<button
								type="button"
								onClick={() => setLockConfirm(null)}
								className="rounded-md border border-slate-700 px-4 py-2"
							>
								Hủy
							</button>
							<button
								type="button"
								disabled={lockState === "loading"}
								onClick={() => handleLock(lockConfirm)}
								className="rounded-md bg-red-500 px-4 py-2 font-medium text-white disabled:opacity-50"
							>
								{lockState === "loading" ? "Đang khóa…" : "Khóa"}
							</button>
						</div>
					</div>
				</div>
			)}
		</section>
	);
}
