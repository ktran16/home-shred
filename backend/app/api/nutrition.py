from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.nutrition import (
    AdaptiveTDEEOut,
    DailyFoodLogOut,
    FoodFactsOut,
    FoodLogCopyDayIn,
    FoodLogIn,
    FoodLogOut,
    FoodLogRecentOut,
    FoodLogTotalsOut,
    MealTemplateIn,
    MealTemplateLogIn,
    MealTemplateOut,
    NutritionHistoryDayOut,
    NutritionHistoryOut,
    NutritionTargetOut,
    SuggestedTargets,
)
from app.services import food_log, food_lookup, food_search, meal_templates
from app.services import nutrition as svc
from app.services.nutrition import ADAPTIVE_MIN_DAYS_SPAN, ADAPTIVE_MIN_SAMPLES
from app.services.profile import get_profile

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/targets", response_model=NutritionTargetOut)
async def get_targets(db: AsyncSession = Depends(get_db)) -> NutritionTargetOut:
    target = await svc.latest(db)
    if target is None:
        raise HTTPException(status_code=404, detail="No nutrition targets yet")
    return NutritionTargetOut.model_validate(target)


@router.post("/recompute", response_model=NutritionTargetOut)
async def recompute(db: AsyncSession = Depends(get_db)) -> NutritionTargetOut:
    target = await svc.recompute(db)
    if target is None:
        raise HTTPException(status_code=409, detail="Set a profile before computing nutrition")
    return NutritionTargetOut.model_validate(target)


@router.get("/log", response_model=DailyFoodLogOut)
async def get_food_log(
    date: date_type | None = None, db: AsyncSession = Depends(get_db)
) -> DailyFoodLogOut:
    return _daily_log_out(await food_log.daily_log(db, date))


@router.post("/log", response_model=DailyFoodLogOut, status_code=201)
async def post_food_log(data: FoodLogIn, db: AsyncSession = Depends(get_db)) -> DailyFoodLogOut:
    entry = await food_log.create_entry(db, data)
    return _daily_log_out(await food_log.daily_log(db, entry.date))


@router.get("/log/recent", response_model=list[FoodLogRecentOut])
async def recent_foods(
    limit: int = Query(default=8, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> list[FoodLogRecentOut]:
    foods = await food_log.recent_foods(db, limit=limit)
    return [
        FoodLogRecentOut(
            name=entry.name,
            grams=entry.grams,
            kcal=entry.kcal,
            protein_g=entry.protein_g,
            carbs_g=entry.carbs_g,
            fat_g=entry.fat_g,
            source=entry.source,
            barcode=entry.barcode,
            last_logged_on=entry.date,
        )
        for entry in foods
    ]


@router.post("/log/copy-day", response_model=DailyFoodLogOut, status_code=201)
async def copy_food_log_day(
    data: FoodLogCopyDayIn,
    db: AsyncSession = Depends(get_db),
) -> DailyFoodLogOut:
    try:
        await food_log.copy_day(db, from_date=data.from_date, to_date=data.to_date)
    except food_log.FoodLogSourceDayEmptyError as exc:
        raise HTTPException(status_code=404, detail="No food logged on source day") from exc
    return _daily_log_out(await food_log.daily_log(db, data.to_date))


@router.get("/log/history", response_model=NutritionHistoryOut)
async def food_log_history(
    end_date: date_type | None = None,
    days: int = Query(default=7, ge=1, le=31),
    db: AsyncSession = Depends(get_db),
) -> NutritionHistoryOut:
    history = await food_log.nutrition_history(db, end_date=end_date, days=days)
    return NutritionHistoryOut(
        start_date=history.start_date,
        end_date=history.end_date,
        days=[
            NutritionHistoryDayOut(
                date=day.date,
                logged=day.logged,
                kcal=day.totals.kcal,
                protein_g=day.totals.protein_g,
                carbs_g=day.totals.carbs_g,
                fat_g=day.totals.fat_g,
                target_kcal=day.target.target_kcal if day.target is not None else None,
                target_protein_g=day.target.protein_g if day.target is not None else None,
                target_carbs_g=day.target.carbs_g if day.target is not None else None,
                target_fat_g=day.target.fat_g if day.target is not None else None,
                kcal_adherent=day.kcal_adherent,
            )
            for day in history.days
        ],
        logged_days=history.logged_days,
        target_days=history.target_days,
        adherent_days=history.adherent_days,
        adherence_pct=history.adherence_pct,
    )


@router.delete("/log/{entry_id}", response_model=DailyFoodLogOut)
async def delete_food_log(entry_id: int, db: AsyncSession = Depends(get_db)) -> DailyFoodLogOut:
    try:
        log_date = await food_log.delete_entry(db, entry_id)
    except food_log.FoodLogNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Food log entry not found") from exc
    return _daily_log_out(await food_log.daily_log(db, log_date))


@router.get("/templates", response_model=list[MealTemplateOut])
async def list_meal_templates(db: AsyncSession = Depends(get_db)) -> list[MealTemplateOut]:
    templates = await meal_templates.list_templates(db)
    return [MealTemplateOut.model_validate(t) for t in templates]


@router.post("/templates", response_model=MealTemplateOut, status_code=201)
async def create_meal_template(
    data: MealTemplateIn, db: AsyncSession = Depends(get_db)
) -> MealTemplateOut:
    """Save a meal template from explicit items or from one day's log (SPEC §19.9 N2)."""
    try:
        if data.from_date is not None:
            template = await meal_templates.create_from_day(db, data.name, data.from_date)
        else:
            template = await meal_templates.create_template(db, data.name, data.items or [])
    except meal_templates.DuplicateMealTemplateError as exc:
        raise HTTPException(
            status_code=409, detail="A meal template with that name already exists"
        ) from exc
    except meal_templates.EmptyMealTemplateError as exc:
        raise HTTPException(
            status_code=422, detail="A meal template needs at least one food"
        ) from exc
    except food_log.FoodLogSourceDayEmptyError as exc:
        raise HTTPException(status_code=404, detail="No food logged on source day") from exc
    return MealTemplateOut.model_validate(template)


@router.post("/templates/{template_id}/log", response_model=DailyFoodLogOut, status_code=201)
async def log_meal_template(
    template_id: int, data: MealTemplateLogIn, db: AsyncSession = Depends(get_db)
) -> DailyFoodLogOut:
    """Log every food in a template (× scale) as ordinary food-log rows."""
    try:
        entries = await meal_templates.log_template(db, template_id, data.date, data.scale)
    except meal_templates.MealTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Meal template not found") from exc
    except meal_templates.MealTemplateScaleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _daily_log_out(await food_log.daily_log(db, entries[0].date))


@router.delete("/templates/{template_id}", status_code=204)
async def delete_meal_template(template_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await meal_templates.delete_template(db, template_id)
    except meal_templates.MealTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Meal template not found") from exc


@router.get("/adaptive", response_model=AdaptiveTDEEOut)
async def adaptive(db: AsyncSession = Depends(get_db)) -> AdaptiveTDEEOut:
    """Adaptive TDEE preview from the bodyweight trend (SPEC §17.3 A1)."""
    if await get_profile(db) is None:
        raise HTTPException(status_code=404, detail="Profile not set")
    est = await svc.adaptive_targets(db)
    if est is None:
        return AdaptiveTDEEOut(
            enough_data=False,
            reason=(
                f"Need at least {ADAPTIVE_MIN_SAMPLES} weigh-ins spanning "
                f"{ADAPTIVE_MIN_DAYS_SPAN}+ days in the last 4 weeks."
            ),
        )
    return AdaptiveTDEEOut(
        enough_data=True,
        samples=est.samples,
        days_span=est.days_span,
        static_tdee_kcal=est.static_tdee_kcal,
        estimated_tdee_kcal=est.estimated_tdee_kcal,
        assumed_intake_kcal=est.assumed_intake_kcal,
        weight_change_kg_per_week=est.weight_change_kg_per_week,
        clamped=est.clamped,
        suggested=SuggestedTargets(
            target_kcal=est.targets.target_kcal,
            protein_g=est.targets.protein_g,
            carbs_g=est.targets.carbs_g,
            fat_g=est.targets.fat_g,
        ),
    )


@router.get("/food/search", response_model=list[FoodFactsOut])
async def food_search_endpoint(
    q: str = Query(min_length=1, max_length=80),
    limit: int = Query(default=10, ge=1, le=25),
    db: AsyncSession = Depends(get_db),
) -> list[FoodFactsOut]:
    """Search foods by name via Open Food Facts (cached locally; SPEC §19.8 W2, opt-in/external)."""
    hits = await food_search.search_foods(db, q, limit=limit)
    return [FoodFactsOut.model_validate(h) for h in hits]


@router.get("/barcode/{code}", response_model=FoodFactsOut)
async def barcode(code: str) -> FoodFactsOut:
    """Look up a barcode's macros from Open Food Facts (SPEC §17.5 B2b, opt-in/external)."""
    try:
        facts = await food_lookup.lookup_barcode(code)
    except food_lookup.FoodNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No product found for that barcode") from exc
    except food_lookup.FoodLookupError as exc:
        raise HTTPException(status_code=502, detail="Open Food Facts lookup failed") from exc
    return FoodFactsOut.model_validate(facts)


@router.post("/adaptive/apply", response_model=NutritionTargetOut)
async def apply_adaptive(db: AsyncSession = Depends(get_db)) -> NutritionTargetOut:
    """Persist today's targets from the adaptive TDEE estimate (SPEC §17.3 A1)."""
    if await get_profile(db) is None:
        raise HTTPException(status_code=409, detail="Set a profile before computing nutrition")
    target = await svc.apply_adaptive(db)
    if target is None:
        raise HTTPException(status_code=409, detail="Not enough bodyweight history to adapt yet")
    return NutritionTargetOut.model_validate(target)


def _daily_log_out(log: food_log.DailyFoodLog) -> DailyFoodLogOut:
    return DailyFoodLogOut(
        date=log.date,
        entries=[FoodLogOut.model_validate(entry) for entry in log.entries],
        totals=FoodLogTotalsOut(
            kcal=log.totals.kcal,
            protein_g=log.totals.protein_g,
            carbs_g=log.totals.carbs_g,
            fat_g=log.totals.fat_g,
        ),
        target=NutritionTargetOut.model_validate(log.target) if log.target is not None else None,
        remaining_kcal=log.remaining_kcal,
        remaining_protein_g=log.remaining_protein_g,
        remaining_carbs_g=log.remaining_carbs_g,
        remaining_fat_g=log.remaining_fat_g,
    )
