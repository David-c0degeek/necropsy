import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Download, ExternalLink, LoaderCircle, RefreshCw } from "lucide-react";
import { request } from "./bridge";

interface UpdateInfo {
  installed_version: string;
  latest_version: string | null;
  available: boolean;
  can_install: boolean;
  restart_required: boolean;
  release_url: string;
  notes: string;
  message: string;
}

export function Updates({
  available,
  version,
  closing,
  onRestart,
}: {
  available: boolean;
  version: string;
  closing: boolean;
  onRestart: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [working, setWorking] = useState("");
  const [info, setInfo] = useState<UpdateInfo | null>(null);
  const [installed, setInstalled] = useState(false);
  const [error, setError] = useState("");
  const dialog = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const close = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open && !closing)
      (close.current?.disabled ? dialog.current : close.current)?.focus();
  }, [open, closing]);

  function dismiss() {
    setOpen(false);
    trigger.current?.focus();
  }

  async function check() {
    if (!available || working) return;
    setOpen(true);
    setWorking("checking");
    setError("");
    try {
      const result = await request<UpdateInfo>("check_updates");
      setInfo(result);
      setInstalled(result.restart_required);
    } catch (error) {
      setInfo(null);
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setWorking("");
    }
  }

  async function install() {
    if (!available || working) return;
    setError("");
    setWorking("installing");
    try {
      if (installed) {
        await request("restart_update");
        await onRestart();
      } else {
        const result = await request<{
          installed: boolean;
          restart_ready: boolean;
        }>("install_update");
        setInstalled(result.installed);
        if (result.restart_ready) await onRestart();
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setWorking("");
    }
  }

  return (
    <>
      <button
        ref={trigger}
        className="theme-button"
        disabled={!available || Boolean(working)}
        onClick={() => void check()}
      >
        <RefreshCw size={17} /> Check for updates
      </button>
      {open &&
        !closing &&
        createPortal(
          <div className="dialog-backdrop">
            <section
              ref={dialog}
              className="close-dialog update-dialog"
              role="dialog"
              aria-modal="true"
              aria-labelledby="update-title"
              tabIndex={-1}
              onKeyDown={(event) => {
                if (event.key === "Escape" && working !== "installing")
                  dismiss();
                if (event.key === "Tab") {
                  const controls = Array.from(
                    event.currentTarget.querySelectorAll<HTMLElement>(
                      'button:not(:disabled), summary, a[href], [tabindex="0"]',
                    ),
                  );
                  const first = controls[0],
                    last = controls[controls.length - 1];
                  if (
                    !first ||
                    (event.shiftKey && document.activeElement === first) ||
                    (!event.shiftKey && document.activeElement === last)
                  ) {
                    event.preventDefault();
                    (event.shiftKey ? last : first)?.focus();
                  }
                }
              }}
            >
              <Download size={28} />
              <h2 id="update-title">App updates</h2>
              <p>
                Installed version:{" "}
                <strong>{info?.installed_version ?? version}</strong>
                {info?.latest_version && (
                  <>
                    {" "}
                    · Latest release: <strong>{info.latest_version}</strong>
                  </>
                )}
              </p>
              {working && (
                <p role="status">
                  <LoaderCircle className="spin" size={16} />{" "}
                  {working === "checking"
                    ? "Checking for updates…"
                    : "Updating Necropsy. The app will restart when ready…"}
                </p>
              )}
              {error && (
                <p role="alert" className="warning-text">
                  {error}
                </p>
              )}
              {info && !working && (
                <p role="status">
                  {installed
                    ? "Update installed. Restart to finish."
                    : info.message}
                </p>
              )}
              {info?.available && !info.can_install && (
                <p>
                  This copy needs a manual update. Open the release page for
                  download options.
                </p>
              )}
              {info?.latest_version && (
                <details>
                  <summary>Release notes</summary>
                  <pre className="update-notes">{info.notes}</pre>
                </details>
              )}
              <p className="field-help">
                Checks published app releases on GitHub. Your saved analyses and
                sign-in are preserved.
              </p>
              <div className="dialog-actions">
                <button
                  ref={close}
                  className="secondary"
                  disabled={working === "installing"}
                  onClick={dismiss}
                >
                  Close
                </button>
                <button
                  className="secondary"
                  disabled={!available || Boolean(working)}
                  onClick={() => void check()}
                >
                  Check again
                </button>
                {info?.available && !info.can_install && (
                  <button
                    className="primary"
                    disabled={!available || Boolean(working)}
                    onClick={() =>
                      void request("open_update_release").catch(
                        (error: unknown) => setError(String(error)),
                      )
                    }
                  >
                    <ExternalLink size={16} /> Open release page
                  </button>
                )}
                {(info?.can_install || installed) && (
                  <button
                    className="primary"
                    disabled={!available || Boolean(working)}
                    onClick={() => void install()}
                  >
                    <Download size={16} />
                    {installed ? "Restart now" : "Update and restart"}
                  </button>
                )}
              </div>
            </section>
          </div>,
          document.body,
        )}
    </>
  );
}
