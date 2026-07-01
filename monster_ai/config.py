"""Configuration loader for Monster AI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class WatchdogSettings(BaseModel):
    enabled: bool = True
    check_ollama: bool = True
    check_comfyui: bool = True
    restart_comfyui: bool = True


class OrchestratorSettings(BaseModel):
    enabled: bool = True
    interval_seconds: int = 60
    check_discord: bool = True
    check_monsterlock: bool = True
    check_ollama: bool = True
    check_api: bool = True
    auto_recover_monsterlock: bool = True


class LearningSettings(BaseModel):
    enabled: bool = True
    data_dir: str = "./data/learning"
    feedback_enabled: bool = True
    preference_learning: bool = True
    knowledge_extraction: bool = True
    reflect_enabled: bool = True
    reflect_max_retries: int = 2
    min_quality_score: float = 0.70
    inject_context_always: bool = True
    regenerate_on_negative_feedback: bool = True
    auto_tune_quality: bool = True
    evolution_log_enabled: bool = True
    web_learning_enabled: bool = True
    web_auto_search: bool = True
    web_search_langs: list[str] = Field(default_factory=lambda: ["zh", "en"])
    web_max_results: int = 3
    web_fetch_timeout_seconds: int = 15
    web_cache_hours: int = 24
    image_learning_enabled: bool = True
    image_auto_apply_learned_tags: bool = True
    roleplay_web_enabled: bool = True
    roleplay_web_auto_search: bool = True
    curriculum_enabled: bool = True
    curriculum_duration_hours: float = 36.0
    curriculum_auto_start: bool = False


class RepairSettings(BaseModel):
    interval_seconds: int = 30
    max_retries: int = 2
    generation_max_retries: int = 2
    mode: str = "full_auto"
    code_repair_enabled: bool = True
    auto_restart: bool = True
    auto_git_commit: bool = True
    run_tests_after_fix: bool = True
    max_auto_repairs_per_hour: int = 3
    max_files_per_fix: int = 5
    rollback_on_test_fail: bool = True
    allowed_paths: list[str] = Field(
        default_factory=lambda: ["monster_ai/", "scripts/", "config.yaml"]
    )
    watchdog: WatchdogSettings = Field(default_factory=WatchdogSettings)
    orchestrator: OrchestratorSettings = Field(default_factory=OrchestratorSettings)


class LLMSettings(BaseModel):
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2:latest"
    num_ctx: int = 4096
    temperature: float = 0.8
    timeout_seconds: int = 120


class ModuleToggle(BaseModel):
    enabled: bool = False


class ImageQualitySettings(BaseModel):
    enabled: bool = True
    mode: str = "rules"  # rules | light | full
    device: str = "cpu"
    max_retries: int = 3
    min_clip_score: float = 0.18
    min_aesthetic: float = 4.5
    save_bad: bool = True
    save_good: bool = True
    escalate_after: int = 3
    fallback_checkpoint: str = "auto"
    allow_high_saturation: bool = False
    allow_dark_style: bool = False
    add_quality_tags: bool = True
    data_dir: str = "./data/quality"
    anti_collapse_lora: str = "anti_collapse.safetensors"
    auto_lora_on_retry: bool = True
    lora_strength_on_retry: float = 0.65
    reject_bad_output: bool = True
    min_alive_score: float = 0.70
    min_high_quality_score: float = 0.85


class ImageModuleSettings(ModuleToggle):
    comfyui_url: str = "http://127.0.0.1:8188"
    default_workflow: str = "sd15_lora"
    checkpoint: str = "auto"
    output_dir: str = "./data/outputs/images"
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg: float = 7.0
    lora_strength: float = 0.8
    quality: ImageQualitySettings = Field(default_factory=ImageQualitySettings)


class WebSettings(BaseModel):
    """Public web UI (Cloudflare Pages + Tunnel)."""

    cors_enabled: bool = True
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:7860",
            "http://localhost:7860",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )
    allow_credentials: bool = True


class DifySettings(BaseModel):
    """Dify workflow orchestration (parallel to Monster native)."""

    enabled: bool = False
    api_url: str = ""
    api_key_env: str = "DIFY_API_KEY"
    workflow_image_id: str = ""
    workflow_multimodal_id: str = ""
    min_quality_score: float = 0.70
    fallback_to_monster: bool = True


class IntegrationsSettings(BaseModel):
    """Third-party platform hooks."""

    make_webhook_secret_env: str = "MAKE_WEBHOOK_SECRET"
    sentry_dsn_env: str = "SENTRY_DSN"
    sentry_enabled: bool = False
    jam_enabled: bool = False
    ahrefs_enabled: bool = False


class CommercialSettings(BaseModel):
    """7-day trial + one-time lifetime unlock."""

    enabled: bool = True
    data_dir: str = "./data/commercial"
    trial_days: int = 7
    unlock_dev_token: str = ""
    min_high_quality_score: float = 0.85


class EcosystemSettings(BaseModel):
    """One-click network ecosystem installer."""

    enabled: bool = True
    data_dir: str = "./data/ecosystem"
    network_install_enabled: bool = True
    require_consent: bool = True
    default_bundle: str = "full"
    allow_r18_bundle: bool = True
    allow_model_downloads: bool = True


class LauncherSettings(BaseModel):
    comfyui_enabled: bool = True
    auto_start_comfyui: bool = True
    comfyui_headless: bool = True
    hide_console: bool = True
    comfyui_path: str = "auto"
    comfyui_url: str = "http://127.0.0.1:8188"
    startup_timeout_seconds: int = 180
    wait_for_comfyui: bool = True
    block_on_comfyui_timeout: bool = False
    auto_download_models: bool = False
    react_ui_enabled: bool = True
    node_api_port: int = 3000
    open_browser: bool = True


class HistorySettings(BaseModel):
    enabled: bool = True
    dir: str = "./data/logs/generation_history"
    retention_days: int = 30
    auto_purge_on_startup: bool = True


class VideoModuleSettings(ModuleToggle):
    comfyui_url: str = "http://127.0.0.1:8188"
    output_dir: str = "./data/outputs/videos"
    training_materials_dir: str = "C:/MonsterAI/Training generative video"
    mode: str = "animatediff"
    max_frames: int = 16
    fps: int = 8
    width: int = 512
    height: int = 512
    steps: int = 15
    output_format: str = "mp4"
    require_ffmpeg: bool = True
    temp_dir: str = "./data/tmp"


class GuardSettings(BaseModel):
    enabled: bool = True
    mode: str = "embedded"  # embedded | standalone
    protection_level: str = "standard"  # light | standard | strict
    action_mode: str = "delete_warn"  # warn_only | delete_warn | mute | quarantine
    ai_backend: str = "auto"  # auto | none | ollama | local_monster_ai
    monster_ai_url: str = ""
    ai_threshold: int = 40
    warn_threshold: int = 50
    block_threshold: int = 80
    rule_sync_url: str = ""
    privacy_retention_hours: int = 72
    chat_bridge_enabled: bool = True
    chat_rate_limit_per_minute: int = 10
    data_dir: str = "./data/guard"
    self_heal_enabled: bool = True
    self_heal_interval_seconds: int = 60
    self_heal_max_backoff_seconds: int = 300
    max_reconnect_attempts: int = 10
    heartbeat_interval_seconds: int = 30
    heartbeat_max_latency_seconds: float = 5.0
    heartbeat_fail_threshold: int = 3
    notify_webhook_url: str = ""
    notify_channel_id: int = 0
    monster_ai_consent_required: bool = True
    mtls_cert_path: str = ""
    mtls_key_path: str = ""
    callguard_bridge_enabled: bool = True
    callguard_poll_interval_seconds: int = 15
    callguard_alert_score_threshold: int = 70
    trial_reminder_enabled: bool = False
    trial_days: int = 7
    welcome_intro_enabled: bool = True
    welcome_intro_style: str = "cyberpunk"  # guardian | cyberpunk | privacy


class DiscordModuleSettings(ModuleToggle):
    token_env: str = "MONSTER_DISCORD_TOKEN"
    application_id_env: str = "MONSTER_DISCORD_APP_ID"
    guard: GuardSettings = Field(default_factory=GuardSettings)


class TTSModuleSettings(ModuleToggle):
    engine: str = "piper"
    piper_voice: str = "zh_CN-huayan-medium"
    xtts_enabled: bool = False
    output_dir: str = "./data/outputs/audio"


class ChatModuleSettings(ModuleToggle):
    enabled: bool = True


class RoleplayModuleSettings(ModuleToggle):
    enabled: bool = True
    max_history: int = 40
    memory_summary_interval: int = 20
    characters_dir: str = "./data/characters"
    chats_dir: str = "./data/chats"


class PromptModuleSettings(ModuleToggle):
    enabled: bool = True
    style: str = "stable_diffusion"


class MiniModuleSettings(ModuleToggle):
    """Mini Monster AI — lightweight uncensored R18+ image stack."""

    enabled: bool = True
    data_dir: str = "./data/mini"
    output_dir: str = "./data/outputs/mini"
    default_template: str = "stable"  # stable | fast | hq | portrait | fullbody
    default_locale: str = "zh-TW"
    checkpoint: str = "auto"
    default_lora: str = ""
    lora_strength: float = 0.75
    lite_mode: bool = True
    uncensored: bool = True
    auto_optimize_prompt: bool = True
    max_quality_retries: int = 6
    reject_bad_output: bool = True
    min_quality_score: float = 0.70
    min_high_quality_score: float = 0.85
    auto_emergency_retry: bool = True
    share_with_monster_ai: bool = True
    network_learning_enabled: bool = False
    network_allow_downloads: bool = False
    network_allow_metrics_upload: bool = False
    network_metrics_endpoint: str = ""
    gguf_model_hint: str = "qwen2.5:7b"
    vram_profile: str = "mini"  # mini | standard
    likeness_enabled: bool = True
    likeness_target_similarity: float = 0.98
    likeness_ipadapter_weight: float = 0.85
    require_user_reference: bool = True
    voice_clone_enabled: bool = True
    multimodal_sync_enabled: bool = True
    comfy_input_dir: str = "./data/comfyui/input"


class ModulesSettings(BaseModel):
    chat: ChatModuleSettings = Field(default_factory=ChatModuleSettings)
    roleplay: RoleplayModuleSettings = Field(default_factory=RoleplayModuleSettings)
    image: ImageModuleSettings = Field(default_factory=ImageModuleSettings)
    video: VideoModuleSettings = Field(default_factory=VideoModuleSettings)
    discord: DiscordModuleSettings = Field(default_factory=DiscordModuleSettings)
    tts: TTSModuleSettings = Field(default_factory=TTSModuleSettings)
    training: ModuleToggle = Field(default_factory=ModuleToggle)
    prompt: PromptModuleSettings = Field(default_factory=PromptModuleSettings)
    mini: MiniModuleSettings = Field(default_factory=MiniModuleSettings)


class EmailNotificationSettings(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    from_addr: str = ""
    to: str = ""
    password_env: str = "MONSTER_SMTP_PASSWORD"


class NotificationSettings(BaseModel):
    webui: bool = True
    discord: bool = False
    discord_webhook: str = ""
    email: EmailNotificationSettings = Field(default_factory=EmailNotificationSettings)


class FirewallSettings(BaseModel):
    enabled: bool = True
    mode: str = "learning"  # learning | active | disabled
    learn_threshold: int = 50
    block_threshold: int = 80
    learn_escalate_count: int = 5
    learn_escalate_window_minutes: int = 10
    ban_duration_minutes: int = 60
    whitelist_ips: list[str] = Field(default_factory=lambda: ["127.0.0.1", "::1"])


class GrokPersonaSettings(BaseModel):
    humor: str = "high"
    directness: str = "high"
    uncensored: bool = True


class PersonaSettings(BaseModel):
    enabled: bool = True
    default_mode: str = "grok"  # grok | custom | off
    allow_user_override: bool = True
    response_locale: str = "zh-TW"  # zh-TW | zh-HK | zh-CN | en
    grok: GrokPersonaSettings = Field(default_factory=GrokPersonaSettings)


class MonsterLockSettings(BaseModel):
    enabled: bool = True
    strength: str = "standard"  # light | standard | strict
    hardened_mode: bool = True
    hardware_binding: bool = True
    bind_gpu: bool = True
    auto_bind_on_first_run: bool = True
    require_binding_file: bool = False
    block_on_mismatch: bool = True
    integrity_check_enabled: bool = True
    digital_signatures_enabled: bool = True
    check_interval_seconds: int = 30
    auto_repair: bool = True
    block_on_tamper: bool = True
    anti_debug_enabled: bool = True
    anti_debug_block_threshold: int = 60
    block_on_analysis: bool = True
    behavior_monitor_enabled: bool = True
    credential_rotation_enabled: bool = True
    credential_rotation_seconds: float = 0.1
    credential_ttl_seconds: float = 0.5
    config_guard_enabled: bool = True
    self_destruct_enabled: bool = True
    self_destruct_on_tamper: bool = True
    self_destruct_on_analysis: bool = True
    corrupt_assets_on_destruct: bool = True
    force_exit_on_destruct: bool = False
    data_dir: str = "./data/monsterlock"
    protected_paths: list[str] = Field(default_factory=list)
    rule_sync_url: str = ""
    encrypt_assets_on_setup: bool = False
    asset_paths: list[str] = Field(
        default_factory=lambda: [
            "data/models/lora",
            "data/models/checkpoints",
            "data/workflows",
        ]
    )


class CallGuardSettings(BaseModel):
    enabled: bool = True
    locale: str = "zh-HK"
    llm_analysis_enabled: bool = True
    auto_reject_threshold: int = 85
    deep_analyze_threshold: int = 60
    threat_db_sync_hours: int = 6
    connection_mode: str = "cloudflare_tunnel"
    tunnel_url_env: str = "MONSTER_TUNNEL_URL"
    tunnel_url_file: str = "./data/callguard/tunnel_url.txt"
    data_dir: str = "./data/callguard"
    report_enabled: bool = True
    consensus_min_votes: int = 3
    consensus_adopt_threshold: int = 70
    public_comment_board: bool = False
    hk_hotline: str = "18222"
    apk_download_url: str = ""
    github_releases_page: str = "https://github.com/SB00001090/Monster-Ai/releases/latest"


class CrimeGuardSettings(BaseModel):
    enabled: bool = True
    locale: str = "zh-HK"
    llm_analysis_enabled: bool = True
    vpn_detection_enabled: bool = True
    vpn_scan_interval_seconds: int = 15
    vpn_scan_on_prompt: bool = True
    device_contact_detection_enabled: bool = True
    device_contact_scan_interval_seconds: int = 10
    device_contact_scan_on_prompt: bool = True
    device_contact_lock_on_high_risk: bool = True
    device_contact_lock_min_score: int = 70
    device_contact_require_usb_or_bt: bool = False
    device_contact_min_connections: int = 1
    escalate_usb_bluetooth_lock: bool = False
    escalate_self_repair_on_lock: bool = True
    network_lock_enabled: bool = True
    lock_mode: str = "localhost_only"  # localhost_only | block_vpn_ports
    allow_local_services: bool = True
    auto_lock_on_crime: bool = True
    vpn_lock_on_high_risk: bool = True
    vpn_lock_min_score: int = 60
    block_chat_when_locked: bool = True
    block_generation_when_locked: bool = True
    block_generation_on_crime: bool = True
    recovery_token: str = "MONSTER-RECOVER-2026"
    data_dir: str = "./data/crimeguard"
    rules_sync_url: str = ""


class ProtectionSettings(BaseModel):
    rate_limit_per_minute: int = 60
    allowed_data_roots: list[str] = Field(default_factory=lambda: ["./data"])
    firewall: FirewallSettings = Field(default_factory=FirewallSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    monsterlock: MonsterLockSettings = Field(default_factory=MonsterLockSettings)
    crimeguard: CrimeGuardSettings = Field(default_factory=CrimeGuardSettings)
    callguard: CallGuardSettings = Field(default_factory=CallGuardSettings)


class GuardianSettings(BaseModel):
    """Monster Guardian AI — cloud sync, OC protection, error learning."""

    enabled: bool = True
    data_dir: str = "./data/guardian"
    cloud_sync_enabled: bool = True
    e2e_encryption_required: bool = True
    ephemeral_chat_default: bool = True
    anti_screenshot_hint: bool = True
    oc_fingerprint_enabled: bool = True
    oc_watermark_enabled: bool = True
    grok_supervision_enabled: bool = True
    min_quality_score: float = 0.70
    oauth_providers: list[str] = Field(default_factory=lambda: ["google", "github"])
    tunnel_url_env: str = "MONSTER_TUNNEL_URL"
    apk_usb_install_enabled: bool = True
    training_encryption_enabled: bool = True
    bind_hardware_key: bool = True
    require_user_passphrase: bool = False
    encrypt_quality_assets: bool = True
    delete_plaintext_after_encrypt: bool = True


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7860
    log_level: str = "info"
    repair: RepairSettings = Field(default_factory=RepairSettings)
    learning: LearningSettings = Field(default_factory=LearningSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    launcher: LauncherSettings = Field(default_factory=LauncherSettings)
    history: HistorySettings = Field(default_factory=HistorySettings)
    persona: PersonaSettings = Field(default_factory=PersonaSettings)
    modules: ModulesSettings = Field(default_factory=ModulesSettings)
    protection: ProtectionSettings = Field(default_factory=ProtectionSettings)
    ecosystem: EcosystemSettings = Field(default_factory=EcosystemSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    dify: DifySettings = Field(default_factory=DifySettings)
    integrations: IntegrationsSettings = Field(default_factory=IntegrationsSettings)
    commercial: CommercialSettings = Field(default_factory=CommercialSettings)
    guardian: GuardianSettings = Field(default_factory=GuardianSettings)
    guard: GuardSettings | None = None

    @property
    def repair_settings(self) -> RepairSettings:
        return self.repair


def _apply_gpu_profile(data: dict[str, Any]) -> dict[str, Any]:
    profile = os.getenv("MONSTER_GPU_PROFILE", "").lower()
    profiles = data.get("profiles", {})
    if profile and profile in profiles:
        llm = data.setdefault("llm", {})
        llm.update(profiles[profile])
    return data


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    if host := os.getenv("MONSTER_HOST"):
        data["host"] = host
    if port := os.getenv("MONSTER_PORT"):
        data["port"] = int(port)
    if model := os.getenv("MONSTER_LLM_MODEL"):
        data.setdefault("llm", {})["model"] = model
    if ollama_url := os.getenv("MONSTER_OLLAMA_URL"):
        data.setdefault("llm", {})["ollama_url"] = ollama_url
    if num_ctx := os.getenv("MONSTER_LLM_NUM_CTX"):
        data.setdefault("llm", {})["num_ctx"] = int(num_ctx)
    if guard_mode := os.getenv("GUARD_MODE"):
        data.setdefault("modules", {}).setdefault("discord", {}).setdefault("guard", {})[
            "mode"
        ] = guard_mode
    if guard_ai := os.getenv("GUARD_AI_BACKEND"):
        data.setdefault("modules", {}).setdefault("discord", {}).setdefault("guard", {})[
            "ai_backend"
        ] = guard_ai
    if monster_ai_url := os.getenv("MONSTER_AI_URL"):
        data.setdefault("modules", {}).setdefault("discord", {}).setdefault("guard", {})[
            "monster_ai_url"
        ] = monster_ai_url
    if ml_strength := os.getenv("MONSTERLOCK_STRENGTH"):
        data.setdefault("protection", {}).setdefault("monsterlock", {})["strength"] = ml_strength
    # MONSTERLOCK_ENABLED env override blocked when config_guard is active (see config_guard.py)
    if os.getenv("MONSTERLOCK_ENABLED", "").lower() in {"0", "false", "no"}:
        ml = data.setdefault("protection", {}).setdefault("monsterlock", {})
        if not ml.get("config_guard_enabled", True):
            ml["enabled"] = False
    return data


def load_settings(config_path: str | Path | None = None) -> Settings:
    root = Path(__file__).resolve().parent.parent
    if config_path is None:
        env_path = os.getenv("MONSTER_CONFIG")
        path = Path(env_path) if env_path else root / "config.yaml"
    else:
        path = Path(config_path)

    data: dict[str, Any] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    data = _apply_gpu_profile(data)
    data = _apply_env_overrides(data)
    return Settings.model_validate(data)