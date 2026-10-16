import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowLeft,
  Check,
  ChevronRight,
  Download,
  FileArchive,
  FolderOpen,
  Library,
  LoaderCircle,
  Moon,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  Sun,
  X,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import {
  chooseExport,
  chooseFolder,
  chooseSnapshot,
  native,
  onClose,
  quit,
  request,
  startEngine,
} from "./bridge";
import { ReportFrame } from "./ReportFrame";
import type {
  Character,
  EngineMessage,
  ReportResult,
  RunResult,
  SavedRun,
} from "./types";

function initialTheme(): string {
  try {
    return localStorage.getItem("necropsy:theme") === "light"
      ? "light"
      : "dark";
  } catch {
    return "dark";
  }
}

function Mark() {
  return (
    <svg viewBox="0 0 40 40" aria-hidden="true">
      <path
        d="M20 2 36 11v18L20 38 4 29V11Z M12 28V12l16 16V12 M4 20h8m16 0h8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
      />
    </svg>
  );
}

export default function App() {
  const [page, setPage] = useState<"new" | "library" | "report">("new");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [activity, setActivity] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [countdown, setCountdown] = useState(0);
  const [browserUrl, setBrowserUrl] = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [url, setUrl] = useState("");
  const [character, setCharacter] = useState<Character | null>(null);
  const [category, setCategory] = useState("");
  const [runs, setRuns] = useState<SavedRun[]>([]);
  const [filter, setFilter] = useState("");
  const [theme, setTheme] = useState(initialTheme);
  const [report, setReport] = useState<ReportResult | null>(null);
  const [reportRun, setReportRun] = useState<SavedRun | null>(null);
  const [reportView, setReportView] = useState<"playbook" | "report">(
    "playbook",
  );
  const [reportLoading, setReportLoading] = useState(false);
  const [reportAnchor, setReportAnchor] = useState("");
  const [closeDialog, setCloseDialog] = useState(false);
  const [quitting, setQuitting] = useState(false);
  const [version, setVersion] = useState("");
  const busyRef = useRef(false);
  const closingRef = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const reportSequence = useRef(0);
  const dialogCancel = useRef<HTMLButtonElement>(null);

  const showError = useCallback(
    (error: unknown) =>
      setError(error instanceof Error ? error.message : String(error)),
    [],
  );
  const refresh = useCallback(
    async () => setRuns(await request<SavedRun[]>("list")),
    [],
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("necropsy:theme", theme);
    } catch {
      /* Optional persistence. */
    }
  }, [theme]);
  useEffect(() => {
    heading.current?.focus();
  }, [page]);
  useEffect(() => {
    if (closeDialog) dialogCancel.current?.focus();
  }, [closeDialog]);

  useEffect(() => {
    let disposed = false;
    let cleanup = () => {};
    let removeClose = () => {};
    const events = (event: EngineMessage) => {
      if (disposed) return;
      if (event.event === "busy") {
        busyRef.current = Boolean(event.data);
        setBusy(Boolean(event.data));
        if (!event.data) {
          setStopping(false);
          setBrowserUrl("");
          void refresh().catch(showError);
        }
      }
      if (event.event === "progress") {
        const message = String(event.data);
        setActivity(message);
        setLogs((current) => [...current.slice(-199), message]);
      }
      if (event.event === "countdown") setCountdown(Number(event.data));
      if (event.event === "browser") setBrowserUrl(String(event.data));
    };
    void (async () => {
      try {
        if (native)
          removeClose = await onClose(() => {
            if (busyRef.current) setCloseDialog(true);
            else {
              closingRef.current = true;
              setQuitting(true);
              void quit().catch(showError);
            }
          });
        cleanup = await startEngine(events, () => {
          if (!disposed && !closingRef.current) {
            setReady(false);
            setBusy(false);
            busyRef.current = false;
            showError(
              "The analysis engine stopped. Restart Necropsy to continue your saved work.",
            );
          }
        });
        if (disposed) {
          cleanup();
          return;
        }
        const hello = await request<{ version: string; runs: SavedRun[] }>(
          "hello",
        );
        if (!disposed) {
          setVersion(hello.version);
          setRuns(hello.runs);
          setReady(true);
        }
      } catch (error) {
        if (!disposed) showError(error);
      }
    })();
    return () => {
      disposed = true;
      cleanup();
      removeClose();
    };
  }, [refresh, showError]);

  async function loadReport(
    run: SavedRun,
    view: "playbook" | "report" = "playbook",
    anchor = "",
  ) {
    const sequence = ++reportSequence.current;
    setReportLoading(true);
    setError("");
    try {
      const result = await request<ReportResult>("report", {
        id: run.id,
        view,
      });
      if (sequence !== reportSequence.current) return;
      setReport(result);
      setReportRun(run);
      setReportView(view);
      setPage("report");
      setReportAnchor(anchor);
      document.documentElement.dataset.class = result.class_key;
    } catch (error) {
      showError(error);
    } finally {
      if (sequence === reportSequence.current) setReportLoading(false);
    }
  }

  async function operation(
    method: string,
    params: Record<string, unknown> = {},
  ) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setStopping(false);
    setError("");
    setNotice("");
    setLogs([]);
    setActivity("Getting things ready…");
    setCountdown(0);
    setBrowserUrl("");
    try {
      if (method === "identify") {
        setCharacter(null);
        const result = await request<Character | { stopped: boolean }>(
          method,
          params,
        );
        if ("stopped" in result) {
          setNotice(
            "Stopped safely. You can try again whenever you are ready.",
          );
          return;
        }
        setCharacter(result);
        setConnected(true);
        setCategory(
          result.categories.length === 1 ? result.categories[0].value : "",
        );
        document.documentElement.dataset.class = result.class_key;
        setActivity("Character found. Choose your spec to continue.");
      } else if (method === "connect") {
        const result = await request<{
          connected?: boolean;
          stopped?: boolean;
        }>(method);
        if (result.connected) {
          setConnected(true);
          setNotice(
            "Warcraft Logs connected. You can now find your character.",
          );
        }
      } else {
        const result = await request<RunResult>(method, params);
        if (result.stopped)
          setNotice(
            "Progress saved. Continue your analysis from the library whenever you are ready.",
          );
        else if (result.run) {
          if (result.partial)
            setNotice(
              "Your analysis is ready with partial coverage. Check the coverage notes in your Playbook.",
            );
          await loadReport(result.run);
        }
      }
      await refresh();
    } catch (error) {
      showError(error);
      void refresh().catch(showError);
    } finally {
      setBusy(false);
      busyRef.current = false;
      setStopping(false);
      setBrowserUrl("");
    }
  }

  async function stop() {
    setStopping(true);
    try {
      await request("stop");
    } catch (error) {
      setStopping(false);
      showError(error);
    }
  }

  async function addFolder() {
    try {
      const path = await chooseFolder();
      if (path) {
        const run = await request<SavedRun>("import", { path });
        await refresh();
        if (run.has_report) await loadReport(run);
        else {
          setPage("library");
          setNotice(
            "Analysis added. Choose Continue analysis to resume your saved work.",
          );
        }
      }
    } catch (error) {
      showError(error);
    }
  }

  async function importSnapshot() {
    try {
      const path = await chooseSnapshot();
      if (path) await operation("snapshot", { path });
    } catch (error) {
      showError(error);
    }
  }

  async function exportReport() {
    if (!reportRun) return;
    try {
      const path = await chooseExport();
      if (path) {
        await request("export", { id: reportRun.id, path });
        setNotice(
          "Package exported. It includes the Playbook, Report, analysis data and evidence.",
        );
      }
    } catch (error) {
      showError(error);
    }
  }

  const openLink = useCallback(
    (url: string) => {
      void request("open_link", { url }).catch(showError);
    },
    [showError],
  );
  const changeView = useCallback(
    (view: "playbook" | "report", anchor = "") => {
      if (reportRun) void loadReport(reportRun, view, anchor);
    },
    [reportRun],
  );
  const available = ready && !busy && !reportLoading;
  const matching = runs.filter((run) =>
    `${run.title} ${run.status}`.toLowerCase().includes(filter.toLowerCase()),
  );
  const minutes = `${Math.floor(countdown / 60)}:${String(countdown % 60).padStart(2, "0")}`;

  return (
    <div className={`app-shell ${page === "report" ? "viewing-report" : ""}`}>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="app-sidebar" aria-label="Main navigation">
        <a href="#main" className="app-brand" onClick={() => setPage("new")}>
          <Mark />
          <span>
            NECROPSY<small>Raid insight. Next-pull clarity.</small>
          </span>
        </a>
        <div className="nav-label">YOUR RAID DESK</div>
        <nav>
          <button
            className={page === "new" ? "nav-item active" : "nav-item"}
            aria-current={page === "new" ? "page" : undefined}
            onClick={() => setPage("new")}
          >
            <Plus size={18} />
            New analysis
          </button>
          <button
            className={page === "library" ? "nav-item active" : "nav-item"}
            aria-current={page === "library" ? "page" : undefined}
            onClick={() => setPage("library")}
          >
            <Library size={18} />
            Your analyses<span className="nav-count">{runs.length}</span>
          </button>
          {report && (
            <button
              className={page === "report" ? "nav-item active" : "nav-item"}
              onClick={() => setPage("report")}
            >
              <FileArchive size={18} />
              Current analysis
            </button>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-note">
            <ShieldCheck size={19} />
            <div>
              Local by design<small>Your reports stay on this computer.</small>
            </div>
          </div>
          <button
            className="theme-button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            {theme === "dark" ? "Light theme" : "Dark theme"}
          </button>
          <small className="version">Necropsy {version} · Classic Era</small>
        </div>
      </aside>

      <div className="app-content">
        <header className="app-topbar">
          <span>
            <span className="live-dot" />
            CLASSIC ERA <span className="separator">/</span> NAXXRAMAS
          </span>
          <span className="account-state">
            {connected ? (
              <>
                <Check size={14} />
                WCL connected
              </>
            ) : (
              "Your next raid starts here"
            )}
          </span>
        </header>
        <main
          id="main"
          className={page === "report" ? "report-main" : "workspace"}
        >
          {error && (
            <div className="feedback error" role="alert">
              <AlertCircle size={20} />
              <div>
                <strong>
                  {ready
                    ? "Let’s get you back on track"
                    : "Could not connect to Necropsy"}
                </strong>
                <p>{error}</p>
                <small>
                  {ready
                    ? "Your saved analyses are still available. Check the message, then try again."
                    : native
                      ? "Restart the app. Your saved analyses and sign-in are retained."
                      : "The full workflow runs in the desktop application."}
                </small>
              </div>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={17} />
              </button>
            </div>
          )}
          {notice && (
            <div className="feedback success" role="status">
              <Check size={20} />
              <p>{notice}</p>
              <button
                className="icon-button"
                aria-label="Dismiss message"
                onClick={() => setNotice("")}
              >
                <X size={17} />
              </button>
            </div>
          )}
          {page === "new" && (
            <>
              <div className="page-heading">
                <p className="eyebrow">FROM YOUR LAST RAID TO YOUR NEXT PULL</p>
                <h1 ref={heading} tabIndex={-1}>
                  A clearer plan for your next raid.
                </h1>
                <p>
                  See what deserves attention, what to change, and the evidence
                  behind it.
                </p>
              </div>
              <div className="new-grid">
                <section
                  className="analysis-panel"
                  aria-labelledby="new-heading"
                >
                  <div className="section-heading">
                    <span className="step-number">01</span>
                    <div>
                      <h2 id="new-heading">Start with your character</h2>
                      <p>One link. Your raid, in focus.</p>
                    </div>
                  </div>
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      if (available) void operation("identify", { url });
                    }}
                  >
                    <label htmlFor="character-url">
                      Warcraft Logs character link
                    </label>
                    <p className="field-help" id="url-help">
                      Open your character on Warcraft Logs and copy the page
                      address.
                    </p>
                    <div className="url-field">
                      <input
                        id="character-url"
                        type="url"
                        required
                        placeholder="https://vanilla.warcraftlogs.com/character/…"
                        autoComplete="off"
                        spellCheck={false}
                        aria-describedby="url-help"
                        value={url}
                        disabled={!available}
                        onChange={(event) => {
                          setUrl(event.target.value);
                          setCharacter(null);
                          delete document.documentElement.dataset.class;
                        }}
                      />
                    </div>
                    <button
                      className="primary find-button"
                      type="submit"
                      disabled={!available || !url.trim()}
                    >
                      {busy && !character ? (
                        <LoaderCircle className="spin" size={17} />
                      ) : (
                        <Search size={17} />
                      )}
                      Find my character
                      <ArrowRight size={17} />
                    </button>
                    <p className="quiet-note">
                      <ShieldCheck size={14} />
                      We’ll guide you through browser sign-in if needed.
                    </p>
                  </form>
                  {character && (
                    <section
                      className="character-result"
                      aria-label="Character found"
                    >
                      <div className="character-heading">
                        <span className="character-initial">
                          {character.name.charAt(0)}
                        </span>
                        <div>
                          <h3>{character.name}</h3>
                          <p>
                            {character.class_name} · {character.server} ·{" "}
                            {character.faction}
                          </p>
                        </div>
                        <Check size={21} />
                      </div>
                      {character.ambiguity && (
                        <>
                          <label htmlFor="partition">
                            Choose your raid history
                          </label>
                          <select
                            id="partition"
                            defaultValue=""
                            disabled={!available}
                            onChange={(event) => {
                              if (event.target.value)
                                void operation("identify", {
                                  url,
                                  partition: Number(event.target.value),
                                });
                            }}
                          >
                            <option value="" disabled>
                              Select a raid partition
                            </option>
                            {character.partitions.map((p) => (
                              <option key={p.id} value={p.id}>
                                {p.name}
                              </option>
                            ))}
                          </select>
                          <p className="field-help">
                            Your character has multiple raid histories. Choose
                            the one to review.
                          </p>
                        </>
                      )}
                      {!character.ready && !character.ambiguity && (
                        <p className="warning-text">
                          We couldn’t verify this character’s faction or raid
                          history. Try another character link.
                        </p>
                      )}
                      {character.ready && character.categories.length > 0 && (
                        <>
                          <label htmlFor="category">What do you play?</label>
                          <select
                            id="category"
                            value={category}
                            disabled={!available}
                            onChange={(event) =>
                              setCategory(event.target.value)
                            }
                          >
                            <option value="" disabled>
                              Choose your spec
                            </option>
                            {character.categories.map((c) => (
                              <option key={c.value} value={c.value}>
                                {c.label}
                              </option>
                            ))}
                          </select>
                          <p className="field-help">
                            Comparisons follow this Warcraft Logs category.
                          </p>
                          <button
                            className="primary full-width"
                            disabled={!available || !category}
                            onClick={() =>
                              void operation("analyze", { category })
                            }
                          >
                            Analyze my character
                            <ArrowRight size={17} />
                          </button>
                        </>
                      )}
                      {character.ready && !character.categories.length && (
                        <p className="warning-text">
                          This character’s class is not supported for Classic
                          Era Naxxramas.
                        </p>
                      )}
                    </section>
                  )}
                  <div className="panel-footer">
                    <span className="tag">Classic Era</span>
                    <span>Naxxramas · All nine classes</span>
                  </div>
                </section>
                <aside
                  className="expect-panel"
                  aria-labelledby="expect-heading"
                >
                  <div className="decorative-mark">
                    <Mark />
                  </div>
                  <p className="eyebrow">KNOW WHAT. KNOW WHY.</p>
                  <h2 id="expect-heading">
                    Less guesswork.
                    <br />A better next pull.
                  </h2>
                  <p>
                    A personal Playbook that turns your raid into a practical
                    plan.
                  </p>
                  <ol className="expect-list">
                    <li>
                      <span>1</span>
                      <div>
                        <strong>Find your priorities</strong>
                        <p>Start with what deserves your attention.</p>
                      </div>
                    </li>
                    <li>
                      <span>2</span>
                      <div>
                        <strong>Prepare for each boss</strong>
                        <p>Clear actions, with your role in mind.</p>
                      </div>
                    </li>
                    <li>
                      <span>3</span>
                      <div>
                        <strong>See the evidence</strong>
                        <p>Fair comparisons. Honest limitations.</p>
                      </div>
                    </li>
                  </ol>
                  <div className="expect-footnote">
                    Your Playbook works offline.
                    <br />
                    Come back to it before the next raid.
                  </div>
                </aside>
              </div>
              <section className="example-panel">
                <span className="example-icon">
                  <Sparkles size={24} />
                </span>
                <div>
                  <h2>Get a feel for your Playbook</h2>
                  <p>
                    Explore a limited Hunter example. No account or character
                    link needed.
                  </p>
                </div>
                <button
                  className="secondary"
                  disabled={!available}
                  onClick={() => void operation("demo")}
                >
                  Try the example
                  <ChevronRight size={17} />
                </button>
              </section>
              {runs.length > 0 && (
                <section className="recent">
                  <div className="section-title-row">
                    <h2>Pick up where you left off</h2>
                    <button
                      className="text-button"
                      onClick={() => setPage("library")}
                    >
                      All analyses
                      <ArrowRight size={15} />
                    </button>
                  </div>
                  {runs.slice(0, 2).map((run) => (
                    <RunRow
                      key={run.id}
                      run={run}
                      available={available}
                      canOpen={ready && !reportLoading}
                      onOpen={() => void loadReport(run)}
                      onResume={() => void operation("resume", { id: run.id })}
                    />
                  ))}
                </section>
              )}
              <p className="bottom-help">
                Already have saved data?{" "}
                <button
                  className="text-button"
                  disabled={!available}
                  onClick={() => void addFolder()}
                >
                  Add an analysis folder
                </button>
                <span>or</span>
                <button
                  className="text-button"
                  disabled={!available}
                  onClick={() => void importSnapshot()}
                >
                  Open a snapshot
                </button>
              </p>
            </>
          )}

          {page === "library" && (
            <>
              <div className="page-heading">
                <p className="eyebrow">YOUR RAID HISTORY, WITH CONTEXT</p>
                <h1 ref={heading} tabIndex={-1}>
                  Your analyses
                </h1>
                <p>
                  Open a Playbook offline, or continue a raid analysis you saved
                  earlier.
                </p>
              </div>
              <div className="library-tools">
                <div className="search-field">
                  <Search size={18} />
                  <input
                    aria-label="Search saved analyses"
                    placeholder="Search character, spec or status…"
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                  />
                </div>
                <button
                  className="secondary"
                  disabled={!available}
                  onClick={() => void addFolder()}
                >
                  <FolderOpen size={17} />
                  Add folder
                </button>
                <button
                  className="secondary"
                  disabled={!available}
                  onClick={() => void importSnapshot()}
                >
                  <FileArchive size={17} />
                  Open snapshot
                </button>
              </div>
              <div className="library-list">
                {matching.map((run) => (
                  <RunRow
                    key={run.id}
                    run={run}
                    available={available}
                    canOpen={ready && !reportLoading}
                    onOpen={() => void loadReport(run)}
                    onResume={() => void operation("resume", { id: run.id })}
                  />
                ))}
              </div>
              {!matching.length && (
                <section className="empty-state">
                  <Library size={36} />
                  <h2>
                    {runs.length
                      ? "No matching analyses"
                      : "Your next insight starts here"}
                  </h2>
                  <p>
                    {runs.length
                      ? "Try another character name, spec or status."
                      : "Start with your character link, try the example, or add a saved analysis folder."}
                  </p>
                  <button
                    className="primary"
                    onClick={() => {
                      if (runs.length) setFilter("");
                      else setPage("new");
                    }}
                  >
                    {runs.length ? "Clear search" : "Start an analysis"}
                    <ArrowRight size={17} />
                  </button>
                </section>
              )}
              <p className="quiet-note library-note">
                <ShieldCheck size={15} />
                Saved reports open without contacting Warcraft Logs. Continuing
                an analysis may need sign-in.
              </p>
            </>
          )}

          {page === "report" && report && (
            <>
              <div className="report-toolbar">
                <button
                  className="text-button"
                  onClick={() => setPage("library")}
                >
                  <ArrowLeft size={17} />
                  Your analyses
                </button>
                <h1 ref={heading} tabIndex={-1}>
                  {report.title}
                </h1>
                <div className="report-tabs" aria-label="Analysis view">
                  {(["playbook", "report"] as const).map((view) => (
                    <button
                      key={view}
                      aria-pressed={reportView === view}
                      disabled={reportLoading}
                      onClick={() => changeView(view)}
                    >
                      {view === "playbook" ? "Playbook" : "Report"}
                    </button>
                  ))}
                </div>
                <button
                  className="secondary"
                  disabled={!available}
                  onClick={() => void exportReport()}
                >
                  <Download size={16} />
                  Export package
                </button>
              </div>
              <p className="report-sandbox-note">
                Saved analysis · works offline · review marks stay on this
                computer
              </p>
              <ReportFrame
                html={report.html}
                theme={theme}
                anchor={reportAnchor}
                onView={changeView}
                onLink={openLink}
              />
            </>
          )}
          {reportLoading && (
            <div className="loading-report" role="status">
              <LoaderCircle className="spin" size={18} />
              Opening your analysis…
            </div>
          )}
        </main>

        {busy && (
          <section className="activity-panel" aria-label="Analysis progress">
            <div className="activity-top">
              <span className="activity-icon">
                <LoaderCircle className="spin" size={20} />
              </span>
              <div className="activity-message">
                <strong>
                  {stopping
                    ? "Saving your progress…"
                    : countdown > 0
                      ? `Continuing automatically in ${minutes}`
                      : browserUrl
                        ? "Finish signing in through your browser"
                        : "Working on your analysis"}
                </strong>
                <p role="status" aria-live="polite">
                  {countdown > 0
                    ? "Warcraft Logs’ hourly allowance is used up. Your progress is saved; keep this window open to continue."
                    : activity}
                </p>
              </div>
              {browserUrl && !stopping && (
                <button
                  className="secondary"
                  onClick={() => openLink(browserUrl)}
                >
                  <ExternalLink size={15} />
                  Open sign-in
                </button>
              )}
              <button
                className="secondary"
                disabled={stopping}
                onClick={() => void stop()}
              >
                <Square size={14} />
                {stopping ? "Saving…" : "Stop and save"}
              </button>
            </div>
            <details className="activity-details">
              <summary>Show activity details</summary>
              <ol aria-label="Activity history">
                {logs.map((line, index) => (
                  <li key={index}>{line}</li>
                ))}
              </ol>
            </details>
            <p className="activity-tip">
              First analyses can take a while. You can stop safely and continue
              from Your analyses.
            </p>
          </section>
        )}
      </div>

      {closeDialog && (
        <div className="dialog-backdrop">
          <section
            className="close-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="close-title"
            aria-describedby="close-description"
            onKeyDown={(event) => {
              if (event.key === "Escape" && !quitting) setCloseDialog(false);
              if (event.key === "Tab") {
                event.preventDefault();
                const buttons =
                  event.currentTarget.querySelectorAll<HTMLButtonElement>(
                    "button:not(:disabled)",
                  );
                const next =
                  document.activeElement === buttons[0]
                    ? buttons[1]
                    : buttons[0];
                next?.focus();
              }
            }}
          >
            <ShieldCheck size={28} />
            <h2 id="close-title">Save your progress before leaving?</h2>
            <p id="close-description">
              We’ll finish the current step safely. You can continue this
              analysis from your library next time.
            </p>
            <div className="dialog-actions">
              <button
                ref={dialogCancel}
                className="secondary"
                disabled={quitting}
                onClick={() => setCloseDialog(false)}
              >
                Keep working
              </button>
              <button
                className="primary"
                disabled={quitting}
                onClick={() => {
                  setQuitting(true);
                  closingRef.current = true;
                  setStopping(true);
                  setActivity("Saving your progress before closing…");
                  void quit().catch((error) => {
                    setQuitting(false);
                    closingRef.current = false;
                    showError(error);
                  });
                }}
              >
                {quitting ? (
                  <>
                    <LoaderCircle className="spin" size={17} />
                    Saving…
                  </>
                ) : (
                  "Save and quit"
                )}
              </button>
            </div>
          </section>
        </div>
      )}
      {quitting && !closeDialog && (
        <div className="dialog-backdrop">
          <p role="status" className="close-dialog">
            <LoaderCircle className="spin" size={20} />
            Closing Necropsy…
          </p>
        </div>
      )}
    </div>
  );
}

function RunRow({
  run,
  available,
  canOpen,
  onOpen,
  onResume,
}: {
  run: SavedRun;
  available: boolean;
  canOpen: boolean;
  onOpen: () => void;
  onResume: () => void;
}) {
  const done = run.status === "Complete" || run.status === "Offline report";
  return (
    <article className="run-row">
      <div className="run-icon">
        <FileArchive size={21} />
      </div>
      <div className="run-info">
        <h3>{run.title}</h3>
        <p>
          {run.when}
          <span>·</span>
          <span className={done ? "status-ready" : "status-saved"}>
            {done ? <Check size={12} /> : null}
            {run.status}
          </span>
        </p>
        {run.detail && <small>{run.detail}</small>}
      </div>
      <div className="run-actions">
        {run.can_resume && (
          <button
            className="secondary"
            disabled={!available}
            onClick={onResume}
          >
            Continue analysis
            <ArrowRight size={16} />
          </button>
        )}
        {run.has_report && (
          <button
            className={run.can_resume ? "text-button" : "secondary"}
            disabled={!canOpen}
            onClick={onOpen}
          >
            Open Playbook
            <ChevronRight size={16} />
          </button>
        )}
      </div>
    </article>
  );
}
