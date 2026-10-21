#!/bin/sh
# Per-user macOS/Linux setup. No Python, uv, Git, shell restart or sudo required.
set -eu
version=0.6.0
uv_version=0.11.21
release="https://github.com/David-c0degeek/necropsy/releases/download/v$version"
wheel_name="necropsy-$version-py3-none-any.whl"
platform=$(uname -s)
case "$platform" in
    Darwin)
        default_root="$HOME/Library/Application Support/Necropsy/app"
        case "$(uname -m)" in
            arm64) gui_platform=macos-arm64 ;;
            x86_64) gui_platform=macos-x86_64 ;;
            *) printf '%s\n' 'Necropsy needs an Apple Silicon or Intel Mac.' >&2; exit 1 ;;
        esac ;;
    Linux)
        default_root="${XDG_DATA_HOME:-$HOME/.local/share}/necropsy/app"
        case "$(uname -m)" in
            x86_64|amd64) gui_platform=linux-x86_64 ;;
            *) printf '%s\n' 'The Linux desktop build currently needs an x86-64 computer.' >&2; exit 1 ;;
        esac ;;
    *) printf '%s\n' 'Please use the Windows installer on Windows.' >&2; exit 1 ;;
esac
gui_name="necropsy-desktop-$version-$gui_platform.tar.gz"
app_root=${NECROPSY_INSTALL_ROOT:-$default_root}
mkdir -p "$app_root"
app_root=$(cd "$app_root" && pwd -P)
work_root=$(mktemp -d "$app_root/.setup-XXXXXXXX")
cleanup() { rm -f "$work_root"/*; rmdir "$work_root" 2>/dev/null || true; }
failed() {
    printf '%s\n' 'Setup could not finish. Check your connection and run the same command again.' \
        'Your reports and sign-in are preserved.' >&2
}
finish() {
    setup_status=$?
    cleanup
    if [ "$setup_status" -ne 0 ]; then failed; fi
    trap - EXIT
    exit "$setup_status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 1' HUP TERM
download() {
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$1" -o "$2"
    elif command -v wget >/dev/null 2>&1; then
        wget --https-only --quiet "$1" -O "$2"
    else
        printf '%s\n' 'This computer needs curl or wget to download the app.' >&2; return 1
    fi
}
setup() {
    printf '%s\n' 'Necropsy setup - getting everything ready for you.' '[1/4] Getting the app...'
    if [ -n "${NECROPSY_BUNDLE_DIR:-}" ]; then
        cp "$NECROPSY_BUNDLE_DIR/$wheel_name" "$work_root/$wheel_name"
        cp "$NECROPSY_BUNDLE_DIR/$gui_name" "$work_root/$gui_name"
        cp "$NECROPSY_BUNDLE_DIR/SHA256SUMS" "$work_root/SHA256SUMS"
    else
        download "$release/$wheel_name" "$work_root/$wheel_name"
        download "$release/$gui_name" "$work_root/$gui_name"
        download "$release/SHA256SUMS" "$work_root/SHA256SUMS"
    fi
    for asset_name in "$wheel_name" "$gui_name"; do
    expected=$(awk -v name="$asset_name" '$2 == name { print $1 }' "$work_root/SHA256SUMS")
    if [ "${#expected}" -ne 64 ]; then
        printf '%s\n' 'The app checksum is missing or ambiguous.' >&2; return 1
    fi
    if command -v sha256sum >/dev/null 2>&1; then
        actual=$(sha256sum "$work_root/$asset_name" | awk '{ print $1 }')
    else
        actual=$(shasum -a 256 "$work_root/$asset_name" | awk '{ print $1 }')
    fi
    if [ "$actual" != "$expected" ]; then
        printf '%s\n' 'The app download was damaged. Nothing was installed. Please retry setup.' >&2
        return 1
    fi
    done
    printf '%s\n' '[2/4] Preparing the app runtime (no Python installation required)...'
    uv_root="$app_root/runtime/uv"
    uv="$uv_root/uv"
    if [ ! -x "$uv" ]; then
        download "https://astral.sh/uv/$uv_version/install.sh" "$work_root/uv-install.sh"
        UV_INSTALL_DIR="$uv_root" UV_NO_MODIFY_PATH=1 sh "$work_root/uv-install.sh"
    fi
    environment_root=$(mktemp -d "$app_root/versions-$version-XXXXXXXX")
    "$uv" --quiet venv --python 3.14 --managed-python "$environment_root"
    python="$environment_root/bin/python"
    printf '%s\n' '[3/4] Installing Necropsy...'
    "$uv" --quiet pip install --python "$python" "$work_root/$wheel_name"
    installed=$("$python" -m necropsy --version)
    if [ "$installed" != "necropsy $version" ]; then
        printf '%s\n' 'The app could not start. Your previous launcher has been preserved.' >&2
        return 1
    fi
    gui_root="$environment_root/gui"
    mkdir -p "$gui_root"
    tar -xzf "$work_root/$gui_name" -C "$gui_root"
    if [ "$platform" = Darwin ]; then
        gui_bundle="$gui_root/Necropsy.app"
        gui="$gui_bundle/Contents/MacOS/necropsy-desktop"
    else
        gui="$gui_root/Necropsy/AppRun"
    fi
    gui_version=$("$gui" --check-install)
    if [ "$gui_version" != "necropsy $version" ]; then
        printf '%s\n' 'The graphical app could not start. Your previous launcher has been preserved.' >&2
        return 1
    fi
    printf '%s\n' '[4/4] Making it easy to open next time...'
    # Store the interpreter as data; never interpolate a home directory into shell code.
    printf '%s\n' "$python" > "$work_root/python-path"
    printf '%s\n' "$gui" > "$work_root/gui-path"
    mv "$work_root/gui-path" "$app_root/gui-path"
    mv "$work_root/python-path" "$app_root/python-path"
    cat > "$work_root/necropsy" <<'LAUNCHER'
#!/bin/sh
set -eu
target=$0
while [ -L "$target" ]; do
    link=$(readlink "$target")
    case "$link" in /*) target=$link ;; *) target=$(dirname "$target")/$link ;; esac
done
app_root=$(CDPATH='' cd -- "$(dirname -- "$target")" && pwd -P)
python=$(cat "$app_root/python-path")
gui=$(cat "$app_root/gui-path")
if [ "$#" -eq 0 ]; then exec "$gui"; fi
export NECROPSY_GUI_PATH="$gui"
exec "$python" -m necropsy "$@"
LAUNCHER
    chmod 755 "$work_root/necropsy"
    mv "$work_root/necropsy" "$app_root/necropsy"
    if [ "${NECROPSY_NO_SHORTCUTS:-0}" != 1 ]; then
        mkdir -p "$HOME/.local/bin"
        ln -sfn "$app_root/necropsy" "$HOME/.local/bin/necropsy"
        if [ "$platform" = Darwin ]; then
            mkdir -p "$HOME/Applications"
            app_shortcut="$HOME/Applications/Necropsy.app"
            if [ ! -e "$app_shortcut" ] || [ -L "$app_shortcut" ]; then
                ln -sfn "$gui_bundle" "$app_shortcut"
            fi
            old_shortcut="$HOME/Applications/Necropsy.command"
            if [ -L "$old_shortcut" ] && [ "$(readlink "$old_shortcut")" = "$app_root/necropsy" ]; then
                rm -f "$old_shortcut"
            fi
        else
            applications="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
            mkdir -p "$applications"
            # Desktop Exec quoted paths require backslash, quote, backtick and dollar escaping.
            desktop_exec=$(printf '%s' "$app_root/necropsy" | sed 's/[\\"`$]/\\&/g; s/%/%%/g')
            cp "$gui_root/Necropsy/necropsy.png" "$app_root/icon.png"
            printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Necropsy' \
                'Comment=Analyze Warcraft Logs and continue saved analyses' \
                "Exec=\"$desktop_exec\"" 'Terminal=false' "Icon=$app_root/icon.png" \
                'Categories=Game;Utility;' > "$applications/necropsy.desktop"
            chmod 755 "$applications/necropsy.desktop"
        fi
        if [ "${NECROPSY_NO_PATH_CHANGE:-0}" != 1 ]; then
            case "${SHELL:-sh}" in
                */zsh) profile="$HOME/.zshrc" ;;
                */bash) profile="$HOME/.bashrc" ;;
                *) profile="$HOME/.profile" ;;
            esac
            path_line='export PATH="$HOME/.local/bin:$PATH" # Necropsy launcher'
            if ! grep -Fq '# Necropsy launcher' "$profile" 2>/dev/null; then
                printf '\n%s\n' "$path_line" >> "$profile"
            fi
        fi
    fi
    printf '%s\n' 'Ready! Next time, open Necropsy from Applications, or type necropsy in a new terminal.'
}
# Keep errexit active inside setup; an unchecked failed command must never publish a launcher.
setup
if [ "${NECROPSY_NO_LAUNCH:-0}" != 1 ]; then
    if [ "$platform" = Darwin ]; then
        open "$gui_bundle"
    else
        nohup "$app_root/necropsy" </dev/null >/dev/null 2>&1 &
    fi
fi
