"""FastAPI application factory."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException


class SPAStaticFiles(StaticFiles):
    """Serve built React UI and fall back to index.html for client-side routes."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            leaf = path.rsplit("/", 1)[-1] if path else ""
            if leaf and "." in leaf and not leaf.startswith("."):
                raise
            return await super().get_response("index.html", scope)

from monster_ai import __version__
from monster_ai.api.guard import router as guard_router
from monster_ai.api.node_proxy import router as node_proxy_router
from monster_ai.api.heal import router as heal_router
from monster_ai.api.learning import router as learning_router
from monster_ai.api.generation import router as generation_router
from monster_ai.api.history import router as history_router
from monster_ai.api.roleplay import router as roleplay_router
from monster_ai.api.routes import router as http_router
from monster_ai.api.security import router as security_router
from monster_ai.api.websocket import router as ws_router
from monster_ai.config import Settings
from monster_ai.core.code_repair_agent import CodeRepairAgent
from monster_ai.core.generation_history import GenerationHistory
from monster_ai.core.generation_repair import GenerationRepair
from monster_ai.core.image_repair import ImageRepairEngine
from monster_ai.core.progress import GenerationProgress
from monster_ai.core.hardware_probe import detect_hardware
from monster_ai.core.self_heal_orchestrator import SelfHealOrchestrator
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.core.vram_guard import VramGuard
from monster_ai.core.watchdog import Watchdog
from monster_ai.modules.chat.service import ChatService
from monster_ai.modules.discord.bot import DiscordService
from monster_ai.modules.image.comfyui import ImageService
from monster_ai.modules.image.quality import ImageQualityScorer
from monster_ai.modules.image.quality_store import QualityStore
from monster_ai.modules.prompt.enhancer import PromptEnhancer
from monster_ai.modules.prompt.refinement import PromptRefiner
from monster_ai.modules.learning import LearningEngine
from monster_ai.modules.registry import ModuleRegistry
from monster_ai.modules.roleplay.service import RoleplayService
from monster_ai.modules.training.lora import TrainingService
from monster_ai.modules.tts.engine import TTSService
from monster_ai.modules.video.service import VideoService
from monster_ai.protection.firewall import FirewallEngine
from monster_ai.protection.guards import RateLimiter
from monster_ai.protection.callguard import CallGuardEngine
from monster_ai.protection.crimeguard import CrimeGuardEngine
from monster_ai.protection.monsterlock import MonsterLockEngine
from monster_ai.protection.tier_orchestrator import ProtectionTierOrchestrator
from monster_ai.api.callguard import router as callguard_router
from monster_ai.api.dify import router as dify_router
from monster_ai.api.ecosystem import router as ecosystem_router
from monster_ai.api.integrations import router as integrations_router
from monster_ai.api.commercial import router as commercial_router
from monster_ai.api.mini import router as mini_router
from monster_ai.api.guardian import router as guardian_router
from monster_ai.modules.dify.bridge import DifyBridge
from monster_ai.modules.guardian import GuardianService
from monster_ai.modules.ecosystem.installer import EcosystemInstaller
from monster_ai.modules.mini.service import MiniMonsterService

logger = logging.getLogger(__name__)


def _init_sentry(settings: Settings) -> None:
    if not settings.integrations.sentry_enabled:
        return
    dsn = os.environ.get(settings.integrations.sentry_dsn_env, "")
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=os.environ.get("MONSTER_ENV", "production"),
        )
        logger.info("Sentry error tracking enabled")
    except ImportError:
        logger.warning("sentry-sdk not installed — pip install sentry-sdk[fastapi]")


def _ensure_data_dirs() -> None:
    for sub in (
        "characters/avatars",
        "chats",
        "voices",
        "logs/generation_history/records",
        "logs/security",
        "personas",
        "outputs/images",
        "outputs/videos",
        "outputs/audio",
        "models/piper",
        "models/lora",
        "models/checkpoints",
        "workflows",
        "quality/bad",
        "quality/good",
        "quality/pending",
        "training/datasets",
        "training/manifests",
        "training/exports",
        "tmp",
        "comfyui/models",
        "guard",
        "monsterlock/backup",
        "monsterlock/vault",
        "crimeguard",
        "callguard",
        "callguard/reports",
        "models/gguf",
        "learning/users",
        "learning/characters",
        "learning/knowledge",
        "mini",
        "mini/network_cache",
        "outputs/mini",
        "ecosystem",
        "guardian/cloud",
        "guardian/chat_vault",
        "guardian/oc_fingerprints",
        "guardian/error_learning",
        "guardian/grok_supervision",
        "guardian/training_vault/good",
        "guardian/training_vault/bad",
        "guardian/training_vault/template",
        "guardian/training_vault/prompt",
        "guardian/training_vault/lora",
    ):
        (Path("./data") / sub).mkdir(parents=True, exist_ok=True)


def _setup_file_logging() -> None:
    log_path = Path("./data/logs/app.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    repair: SelfRepairEngine = app.state.repair
    history: GenerationHistory = app.state.history
    watchdog: Watchdog = app.state.watchdog
    self_heal: SelfHealOrchestrator = app.state.self_heal
    monsterlock: MonsterLockEngine = app.state.monsterlock
    crimeguard: CrimeGuardEngine = app.state.crimeguard
    callguard: CallGuardEngine = app.state.callguard
    removed = history.purge_on_startup()
    if removed:
        logger.info("Purged %s old history entries", removed)
    await monsterlock.start()
    await crimeguard.start()
    await callguard.start()
    await repair.start()
    await watchdog.start()
    await self_heal.start()

    discord_svc = getattr(app.state, "discord", None)
    if discord_svc is not None:
        await discord_svc.start_guard(
            app.state.repair,
            app.state.chat,
            app.state.roleplay,
        )

    yield

    if discord_svc is not None:
        await discord_svc.stop_guard()
    await self_heal.stop()
    await watchdog.stop()
    await repair.stop()
    await crimeguard.stop()
    await callguard.stop()
    await monsterlock.stop()


def create_app(settings: Settings) -> FastAPI:
    _ensure_data_dirs()
    _setup_file_logging()
    _init_sentry(settings)

    app = FastAPI(
        title="Monster AI",
        description="Local-first, modular AI platform",
        version=__version__,
        lifespan=lifespan,
    )

    if settings.web.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.web.cors_origins,
            allow_origin_regex=r"https://.*\.pages\.dev",
            allow_credentials=settings.web.allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    root = Path(__file__).resolve().parent.parent
    probe = detect_hardware()
    tier_result = ProtectionTierOrchestrator(settings, probe).apply()
    logger.info("Hardware tier: %s (%s)", probe.tier, probe.gpu_name or "no-gpu")
    firewall = FirewallEngine(settings.protection.firewall, settings.protection.notifications)
    monsterlock = MonsterLockEngine(
        settings.protection.monsterlock,
        root,
        notify=firewall.hub,
    )
    if not monsterlock.bootstrap():
        raise RuntimeError(
            f"MonsterLock blocked startup: {monsterlock.state.last_error or 'protection policy'}"
        )
    crimeguard = CrimeGuardEngine(
        settings.protection.crimeguard,
        root,
        notify=firewall.hub,
        repair_engine=None,
        monsterlock=monsterlock,
    )
    repair = SelfRepairEngine(
        settings, root=root, probe=probe, tier_result=tier_result
    )
    crimeguard.repair = repair
    callguard = CallGuardEngine(
        settings.protection.callguard,
        root,
        repair_engine=repair,
        monsterlock=monsterlock,
    )
    gen_repair = GenerationRepair(max_retries=settings.repair.generation_max_retries)
    vram_guard = VramGuard()
    gen_progress = GenerationProgress()
    history = GenerationHistory(settings.history)
    code_repair = CodeRepairAgent(settings.repair, repair, root)
    watchdog = Watchdog(settings, code_repair, firewall.hub, root)
    prompt_enhancer = PromptEnhancer(settings, repair)
    quality_scorer = ImageQualityScorer(settings.modules.image.quality)
    guardian_svc = GuardianService(
        settings.guardian,
        repair=repair,
        learning=None,
        repo_root=root,
        hardware_fingerprint=monsterlock.state.fingerprint,
    )
    quality_store = QualityStore(
        settings.modules.image.quality.data_dir,
        settings.modules.image.quality,
        training_vault=guardian_svc.training_vault,
        encrypt_training=(
            settings.guardian.training_encryption_enabled
            and settings.guardian.encrypt_quality_assets
            and guardian_svc.training_vault is not None
        ),
    )
    image_repair = ImageRepairEngine(settings.modules.image.quality)
    prompt_refiner = PromptRefiner(repair)
    learning = LearningEngine(settings.learning, repair)
    from monster_ai.modules.learning.image_knowledge import ImageKnowledgeLearner

    image_learner = ImageKnowledgeLearner(
        learning.store,
        settings.modules.image.quality,
        settings.learning,
        repair,
        quality_store=quality_store,
    )
    learning.bind_image_learner(image_learner)
    guardian_svc.learning = learning

    def _web_network_allowed() -> tuple[bool, str]:
        if crimeguard.state.network_locked:
            return False, "network_locked"
        return True, ""

    learning.web.set_network_guard(_web_network_allowed)
    ecosystem = EcosystemInstaller(
        settings.ecosystem,
        root=root,
        network_guard=_web_network_allowed,
    )
    self_heal = SelfHealOrchestrator(settings.repair.orchestrator, root)

    chat = ChatService(repair, settings, learning=learning)
    image = ImageService(
        settings,
        repair,
        gen_repair,
        vram_guard,
        prompt_enhancer,
        quality_scorer,
        quality_store,
        image_repair,
        prompt_refiner,
        history=history,
        image_learner=image_learner,
    )
    roleplay = RoleplayService(
        settings, repair, image_service=image, history=history, learning=learning
    )
    video = VideoService(
        settings,
        repair,
        gen_repair,
        vram_guard,
        prompt_enhancer,
        image,
        gen_progress,
        history=history,
    )
    tts = TTSService(settings, gen_repair, vram_guard, history=history)

    modules = ModuleRegistry(settings)
    modules.register(chat)
    modules.register(roleplay)
    modules.register(image)
    modules.register(video)
    discord_svc = DiscordService(settings)
    self_heal.bind(repair=repair, watchdog=watchdog, discord=discord_svc, learning=learning)
    modules.register(learning)
    modules.register(discord_svc)
    modules.register(tts)
    modules.register(TrainingService(settings, root))
    mini_svc = MiniMonsterService(
        settings.modules.mini,
        image,
        repair,
        learning=learning,
        tts=tts,
        network_guard=_web_network_allowed,
    )
    modules.register(mini_svc)
    modules.register(guardian_svc)

    @app.middleware("http")
    async def firewall_middleware(request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        body_preview = ""
        if request.method in {"POST", "PATCH", "PUT"}:
            try:
                body = await request.body()
                body_preview = body[:2048].decode("utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                pass
        allowed, reason = await firewall.check_request(
            ip=ip,
            path=request.url.path,
            method=request.method,
            query=str(request.url.query),
            body_preview=body_preview,
        )
        if not allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Blocked by firewall: {reason}"},
            )
        response = await call_next(request)
        path = request.url.path
        if path in {"/", "/index.html"} or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        if response.status_code == 404:
            firewall.record_404(ip)
        return response

    app.state.settings = settings
    app.state.repair = repair
    app.state.gen_repair = gen_repair
    app.state.image_repair = image_repair
    app.state.history = history
    app.state.firewall = firewall
    app.state.monsterlock = monsterlock
    app.state.crimeguard = crimeguard
    app.state.callguard = callguard
    app.state.hardware_probe = probe
    app.state.tier_result = tier_result
    app.state.watchdog = watchdog
    app.state.self_heal = self_heal
    app.state.learning = learning
    app.state.code_repair = code_repair
    app.state.vram_guard = vram_guard
    app.state.gen_progress = gen_progress
    app.state.chat = chat
    app.state.roleplay = roleplay
    app.state.image = image
    app.state.video = video
    app.state.tts = tts
    app.state.modules = modules
    app.state.discord = discord_svc
    app.state.mini = mini_svc
    app.state.guardian = guardian_svc
    app.state.ecosystem = ecosystem
    app.state.dify = DifyBridge(settings.dify)
    app.state.rate_limiter = RateLimiter(settings.protection.rate_limit_per_minute)
    app.state.version = __version__

    app.include_router(http_router)
    app.include_router(generation_router)
    app.include_router(history_router)
    app.include_router(security_router)
    app.include_router(callguard_router)
    app.include_router(guard_router)
    app.include_router(heal_router)
    app.include_router(learning_router)
    app.include_router(mini_router)
    app.include_router(ecosystem_router)
    app.include_router(dify_router)
    app.include_router(integrations_router)
    app.include_router(commercial_router)
    app.include_router(guardian_router)
    app.include_router(roleplay_router)
    app.include_router(ws_router)
    app.include_router(node_proxy_router)

    project_root = Path(__file__).resolve().parents[1]
    dist_dir = project_root / "dist"
    if dist_dir.is_dir():
        app.mount("/downloads", StaticFiles(directory=dist_dir), name="downloads")
    mini_static = Path(__file__).parent / "web" / "static" / "mini"
    if mini_static.is_dir():
        app.mount("/mini", StaticFiles(directory=mini_static, html=True), name="mini_ui")
    ecosystem_static = Path(__file__).parent / "web" / "static" / "ecosystem"
    if ecosystem_static.is_dir():
        app.mount(
            "/ecosystem",
            StaticFiles(directory=ecosystem_static, html=True),
            name="ecosystem_ui",
        )
    built_ui = project_root / "dist" / "public"
    static_dir = built_ui if built_ui.is_dir() else Path(__file__).parent / "web" / "static"
    app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="static")

    return app