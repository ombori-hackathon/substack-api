"""Category management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models.category import Category, SYSTEM_CATEGORIES
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.category import (
    AvailableIconsResponse,
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
    VALID_SF_SYMBOLS,
)

router = APIRouter(prefix="/categories", tags=["categories"])

MAX_CUSTOM_CATEGORIES = 20


def utc_now():
    return datetime.now(timezone.utc)


def ensure_system_categories(db: Session) -> None:
    """Ensure system categories exist in the database."""
    existing_system = db.query(Category).filter(Category.is_system == True).first()
    if existing_system:
        return

    for cat_data in SYSTEM_CATEGORIES:
        category = Category(
            user_id=None,
            name=cat_data["name"],
            icon=cat_data["icon"],
            color=cat_data["color"],
            is_system=True,
            display_order=cat_data["display_order"],
        )
        db.add(category)
    db.commit()


def get_subscription_counts(db: Session, user_id: int) -> dict[int, int]:
    """Get subscription counts per category for a user."""
    counts = (
        db.query(Subscription.category_id, func.count(Subscription.id))
        .filter(
            Subscription.user_id == user_id,
            Subscription.deleted_at.is_(None),
            Subscription.category_id.isnot(None),
        )
        .group_by(Subscription.category_id)
        .all()
    )
    return {cat_id: count for cat_id, count in counts}


def category_to_response(category: Category, subscription_count: int = 0) -> CategoryResponse:
    """Convert a Category model to CategoryResponse."""
    return CategoryResponse(
        id=category.id,
        name=category.name,
        icon=category.icon,
        color=category.color,
        is_system=category.is_system,
        display_order=category.display_order,
        subscription_count=subscription_count,
    )


@router.get("/icons", response_model=AvailableIconsResponse)
async def list_available_icons(
    current_user: User = Depends(get_current_user),
):
    """List all available SF Symbol icons for categories."""
    return AvailableIconsResponse(icons=sorted(list(VALID_SF_SYMBOLS)))


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all categories (system + user's custom)."""
    ensure_system_categories(db)

    # Get system categories and user's custom categories
    categories = (
        db.query(Category)
        .filter(
            or_(
                Category.is_system == True,
                Category.user_id == current_user.id,
            ),
            Category.deleted_at.is_(None),
        )
        .order_by(Category.display_order, Category.name)
        .all()
    )

    # Get subscription counts
    subscription_counts = get_subscription_counts(db, current_user.id)

    # Count custom categories
    custom_count = sum(1 for c in categories if not c.is_system)

    return CategoryListResponse(
        items=[
            category_to_response(c, subscription_counts.get(c.id, 0))
            for c in categories
        ],
        total_count=len(categories),
        custom_count=custom_count,
        max_custom_allowed=MAX_CUSTOM_CATEGORIES,
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom category."""
    ensure_system_categories(db)

    # Check if user has reached max custom categories
    custom_count = (
        db.query(Category)
        .filter(
            Category.user_id == current_user.id,
            Category.deleted_at.is_(None),
        )
        .count()
    )
    if custom_count >= MAX_CUSTOM_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {MAX_CUSTOM_CATEGORIES} custom categories allowed",
        )

    # Check for duplicate name (case-insensitive) among user's categories and system categories
    existing = (
        db.query(Category)
        .filter(
            func.lower(Category.name) == category_data.name.lower(),
            or_(
                Category.is_system == True,
                Category.user_id == current_user.id,
            ),
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{category_data.name}' already exists",
        )

    # Create the category
    category = Category(
        user_id=current_user.id,
        name=category_data.name,
        icon=category_data.icon,
        color=category_data.color,
        is_system=False,
        display_order=100,  # Custom categories at the end
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    return category_to_response(category)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific category by ID."""
    ensure_system_categories(db)

    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            or_(
                Category.is_system == True,
                Category.user_id == current_user.id,
            ),
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Get subscription count
    subscription_counts = get_subscription_counts(db, current_user.id)

    return category_to_response(category, subscription_counts.get(category.id, 0))


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a category (name for custom, icon/color for any)."""
    ensure_system_categories(db)

    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            or_(
                Category.is_system == True,
                Category.user_id == current_user.id,
            ),
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # System categories cannot have their name changed
    if category.is_system and category_data.name is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rename system category",
        )

    # Check for duplicate name if renaming
    if category_data.name is not None and category_data.name.lower() != category.name.lower():
        existing = (
            db.query(Category)
            .filter(
                func.lower(Category.name) == category_data.name.lower(),
                or_(
                    Category.is_system == True,
                    Category.user_id == current_user.id,
                ),
                Category.deleted_at.is_(None),
                Category.id != category_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category '{category_data.name}' already exists",
            )
        category.name = category_data.name

    if category_data.icon is not None:
        category.icon = category_data.icon

    if category_data.color is not None:
        category.color = category_data.color

    category.updated_at = utc_now()
    db.commit()
    db.refresh(category)

    # Get subscription count
    subscription_counts = get_subscription_counts(db, current_user.id)

    return category_to_response(category, subscription_counts.get(category.id, 0))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom category (reassigns subscriptions to 'Other')."""
    ensure_system_categories(db)

    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == current_user.id,  # Only custom categories can be deleted
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if not category:
        # Check if it's a system category
        system_category = (
            db.query(Category)
            .filter(
                Category.id == category_id,
                Category.is_system == True,
                Category.deleted_at.is_(None),
            )
            .first()
        )
        if system_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system category",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Find the "Other" system category
    other_category = (
        db.query(Category)
        .filter(
            Category.name == "Other",
            Category.is_system == True,
        )
        .first()
    )

    # Reassign subscriptions to "Other" category
    if other_category:
        db.query(Subscription).filter(
            Subscription.category_id == category_id,
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        ).update({Subscription.category_id: other_category.id})

    # Soft delete the category
    category.deleted_at = utc_now()
    db.commit()
