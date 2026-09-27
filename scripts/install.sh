#!/usr/bin/env bash
# Agent Eval Engine macOS / Linux インストーラー
set -euo pipefail

REPO="itsuki911/agent-eval-engine"
VERSION="${1:-latest}"
INSTALL_DIR="/usr/local/bin"

echo "============================================================"
echo "       Agent Eval Engine macOS / Linux インストーラー"
echo "============================================================"

# OS の判定
OS_TYPE="$(uname -s)"
case "${OS_TYPE}" in
    Darwin)
        PLATFORM="darwin"
        DATA_CONFIG_DIR="${HOME}/Library/Application Support/AgentEvalEngine/config"
        ;;
    Linux)
        PLATFORM="linux"
        DATA_CONFIG_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/agent-eval-engine/config"
        ;;
    *)
        echo "【エラー】未対応の OS です: ${OS_TYPE}" >&2
        exit 1
        ;;
esac

# アーキテクチャの判定
ARCH_TYPE="$(uname -m)"
case "${ARCH_TYPE}" in
    x86_64)
        ARCH="amd64"
        ;;
    arm64|aarch64)
        ARCH="arm64"
        ;;
    *)
        echo "【エラー】未対応のアーキテクチャです: ${ARCH_TYPE}" >&2
        exit 1
        ;;
esac

ASSET_NAME="agent-eval_${PLATFORM}_${ARCH}.tar.gz"
echo "対象プラットフォーム: ${PLATFORM}/${ARCH}"

# 作業用一時ディレクトリ
TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

# ダウンロード URL の生成
if [ "${VERSION}" = "latest" ]; then
    BASE_URL="https://github.com/${REPO}/releases/latest/download"
else
    BASE_URL="https://github.com/${REPO}/releases/download/${VERSION}"
fi

echo "GitHub Releases から ${ASSET_NAME} を取得中..."
curl -sSLf "${BASE_URL}/${ASSET_NAME}" -o "${TMP_DIR}/${ASSET_NAME}"

echo "checksums.txt を取得中..."
curl -sSLf "${BASE_URL}/checksums.txt" -o "${TMP_DIR}/checksums.txt"

# SHA-256 チェックサムの検証
echo "SHA-256 チェックサムを検証しています..."
EXPECTED_HASH="$(grep "${ASSET_NAME}" "${TMP_DIR}/checksums.txt" | awk '{print $1}')"
if [ -z "${EXPECTED_HASH}" ]; then
    echo "【エラー】checksums.txt 内に ${ASSET_NAME} のエントリが見つかりません。" >&2
    exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_HASH="$(sha256sum "${TMP_DIR}/${ASSET_NAME}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
    ACTUAL_HASH="$(shasum -a 256 "${TMP_DIR}/${ASSET_NAME}" | awk '{print $1}')"
else
    echo "【警告】sha256sum / shasum コマンドが見つからないため、チェックサム検証をスキップします。"
    ACTUAL_HASH="${EXPECTED_HASH}"
fi

if [ "${ACTUAL_HASH}" != "${EXPECTED_HASH}" ]; then
    echo "【セキュリティエラー】SHA-256 チェックサムが一致しません！" >&2
    echo "計算値: ${ACTUAL_HASH}" >&2
    echo "期待値: ${EXPECTED_HASH}" >&2
    exit 1
fi
echo "✓ SHA-256 チェックサム検証に合格しました: ${ACTUAL_HASH}"

# アーカイブの展開
echo "アーカイブを展開中..."
tar -xzf "${TMP_DIR}/${ASSET_NAME}" -C "${TMP_DIR}"

# インストール先ディレクトリの決定 (権限に応じて /usr/local/bin または ~/.local/bin)
TARGET_DIR="${INSTALL_DIR}"
if [ ! -w "${INSTALL_DIR}" ]; then
    if [ "$(id -u)" -ne 0 ]; then
        if sudo -v 2>/dev/null; then
            SUDO="sudo"
        else
            TARGET_DIR="${HOME}/.local/bin"
            mkdir -p "${TARGET_DIR}"
            SUDO=""
        fi
    else
        SUDO=""
    fi
else
    SUDO=""
fi

echo "バイナリを配置中 (${TARGET_DIR}/agent-eval)..."
${SUDO} mv "${TMP_DIR}/agent-eval" "${TARGET_DIR}/agent-eval"
${SUDO} chmod +x "${TARGET_DIR}/agent-eval"
echo "✓ バイナリを配置しました: ${TARGET_DIR}/agent-eval"

# リポジトリパスの自動検出と保存 (スクリプトがリポジトリ内で実行された場合)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_COMPOSE="${SCRIPT_DIR}/../docker-compose.yml"
if [ -f "${REPO_COMPOSE}" ]; then
    REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
    mkdir -p "${DATA_CONFIG_DIR}"
    echo "${REPO_ROOT}" > "${DATA_CONFIG_DIR}/repo_root.txt"
    echo "✓ リポジトリパスを登録しました (AGENT_EVAL_ROOT): ${REPO_ROOT}"
fi

# PATH 確認
if ! command -v agent-eval >/dev/null 2>&1; then
    echo ""
    echo "【PATH 設定】"
    echo "PATH に ${TARGET_DIR} が含まれていません。~/.bashrc または ~/.zshrc に以下を追加してください:"
    echo "  export PATH=\"${TARGET_DIR}:\$PATH\""
fi

echo ""
echo "============================================================"
echo "✓ agent-eval のインストールが正常に完了しました！"
echo "============================================================"
echo "次のステップ:"
echo "  1. 初期設定: agent-eval init"
echo "  2. 環境診断: agent-eval doctor"
echo "  3. 画面起動: agent-eval (TUI)"
echo ""
