import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, type Me, api } from "./api";

export const TASK_POLL_FIRST_MS = 1000;
export const TASK_POLL_LATER_MS = 2000;
export const TASK_POLL_MAX_SECONDS = 60;

type AssignmentItem = { id: number; title: string; published: boolean };
type GradeResult = { score: number; feedback: string; sources?: string[] };
type TaskView = {
  task_id: string;
  status: string;
  attempts: number;
  error?: string;
  result?: GradeResult;
};

const statusLabel: Record<string, string> = {
  pending: "等待批改",
  running: "正在批改",
  succeeded: "批改完成",
  failed: "批改失败",
  dead: "已停止处理",
};

function errorText(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return "登录已过期，请重新登录。";
    if (err.status === 403) return "当前账号没有这个操作权限。";
    if (err.status === 404) return "找不到这份作业或提交，它可能不属于本班。";
    if (err.status === 503) return "服务暂时不可用，请稍后重试。";
    if (err.status === 400) return "提交内容需要 1 到 20000 字，请修改后再试。";
  }
  return "请求失败，请稍后重试。";
}

export function AssignmentsPage({
  me,
  onLogout,
  push,
}: {
  me: Me;
  onLogout: () => void;
  push: (text: string) => void;
}) {
  const navigate = useNavigate();
  const [items, setItems] = useState<AssignmentItem[] | null>(null);
  const [loadError, setLoadError] = useState("");
  const [selected, setSelected] = useState<number | "">("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const [submissionId, setSubmissionId] = useState<number | null>(null);
  const [task, setTask] = useState<TaskView | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const pollStarted = useRef<number | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    api<{ assignments: AssignmentItem[] }>("/api/assignments")
      .then((data) => {
        setItems(data.assignments);
        if (data.assignments.length === 1) setSelected(data.assignments[0].id);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { replace: true });
          return;
        }
        setLoadError(errorText(err));
      });
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [navigate]);

  function stopPolling() {
    if (timer.current) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  }

  function schedulePoll(taskId: string, startedAt: number) {
    const elapsed = Date.now() - startedAt;
    if (elapsed >= TASK_POLL_MAX_SECONDS * 1000) {
      setTimedOut(true);
      stopPolling();
      return;
    }
    const delay = elapsed < 10_000 ? TASK_POLL_FIRST_MS : TASK_POLL_LATER_MS;
    timer.current = window.setTimeout(() => {
      void pollOnce(taskId, startedAt);
    }, delay);
  }

  async function pollOnce(taskId: string, startedAt: number) {
    try {
      const view = await api<TaskView>(`/api/tasks/${taskId}`);
      setTask(view);
      if (view.status === "succeeded" || view.status === "failed" || view.status === "dead") {
        stopPolling();
        return;
      }
      schedulePoll(taskId, startedAt);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        stopPolling();
        navigate("/login", { replace: true });
        return;
      }
      setFormError(errorText(err));
      schedulePoll(taskId, startedAt);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (selected === "" || busy) return;
    setBusy(true);
    setFormError("");
    setTimedOut(false);
    setTask(null);
    stopPolling();
    try {
      const submitted = await api<{ submission_id: number; version: number; status: string }>(
        `/api/assignments/${selected}/submissions`,
        { method: "POST", body: JSON.stringify({ body }) },
      );
      setSubmissionId(submitted.submission_id);
      const accepted = await api<{ task_id: string; status: string; status_url: string }>(
        `/api/submissions/${submitted.submission_id}/grade`,
        { method: "POST", body: JSON.stringify({}) },
      );
      const view: TaskView = { task_id: accepted.task_id, status: accepted.status, attempts: 0 };
      setTask(view);
      pollStarted.current = Date.now();
      schedulePoll(accepted.task_id, pollStarted.current);
      push("已提交，正在等待批改");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login", { replace: true });
        return;
      }
      setFormError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function refresh() {
    if (!task?.task_id) return;
    setTimedOut(false);
    pollStarted.current = Date.now();
    void pollOnce(task.task_id, pollStarted.current);
  }

  const terminal = task && (task.status === "succeeded" || task.status === "failed" || task.status === "dead");

  return (
    <div className="app-shell">
      <header className="top">
        <div className="ask-brand">
          <p className="ask-kicker">CAMPUSCLAW</p>
          <h1>{me.class_name}班作业</h1>
          <span>
            {me.username} · {me.role === "teacher" ? "教师" : "学生"}
          </span>
        </div>
        <div className="top-actions">
          <button type="button" onClick={() => navigate("/materials")}>
            材料
          </button>
          <button type="button" className="nav-ask" onClick={() => navigate("/ask")}>
            问答
          </button>
          <button type="button" onClick={onLogout}>
            登出
          </button>
        </div>
      </header>
      {items === null && !loadError ? <p className="boot">正在确认作业…</p> : null}
      {loadError ? <p className="form-error">{loadError}</p> : null}
      {items && items.length === 0 ? (
        <p className="empty">还没有已发布作业。等教师发布后再来提交。</p>
      ) : null}
      {items && items.length > 0 ? (
        <section className="login-card" style={{ margin: "24px auto", width: "min(720px, calc(100% - 32px))" }}>
          <h2>提交作业</h2>
          <p className="lede">提交后立即进入异步批改。完成前不会显示分数。</p>
          {me.role !== "student" ? (
            <p className="form-error">教师不能以学生身份提交作业。</p>
          ) : (
            <form onSubmit={onSubmit}>
              <label>
                已发布作业
                <select
                  value={selected}
                  onChange={(e) => setSelected(e.target.value ? Number(e.target.value) : "")}
                  required
                >
                  <option value="">请选择</option>
                  {items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                作答正文
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={8}
                  required
                  maxLength={20000}
                  aria-label="作答正文"
                />
              </label>
              {formError ? <p className="form-error">{formError}</p> : null}
              <button className="primary" type="submit" disabled={busy}>
                {busy ? "正在提交…" : "提交并批改"}
              </button>
            </form>
          )}
          {submissionId ? <p className="lede">当前提交编号 {submissionId}</p> : null}
          {task ? (
            <section className="ask-card" style={{ marginTop: 16 }}>
              <h2>{statusLabel[task.status] ?? task.status}</h2>
              {task.status === "pending" || task.status === "running" ? (
                <p>正在处理，完成后才显示分数。</p>
              ) : null}
              {task.status === "succeeded" && task.result ? (
                <>
                  <p>分数：{task.result.score}</p>
                  <p>{task.result.feedback}</p>
                  {task.result.sources?.length ? <p>出处：{task.result.sources.join("；")}</p> : null}
                </>
              ) : null}
              {(task.status === "failed" || task.status === "dead") && (
                <>
                  <p>{task.error || "批改没有完成。"}</p>
                  <p>已停止处理，请联系教师。</p>
                </>
              )}
              {timedOut && !terminal ? (
                <p>
                  已停止自动刷新。
                  <button type="button" onClick={refresh}>
                    手动刷新
                  </button>
                </p>
              ) : null}
            </section>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
