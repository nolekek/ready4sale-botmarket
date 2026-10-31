from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Category(Base):
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer, default=0)
    
    products: Mapped[list["Product"]] = relationship(back_populates="category", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Float)
    product_type: Mapped[str] = mapped_column(String(20), default="unique")  # "unique", "infinite"
    static_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    category: Mapped["Category"] = relationship(back_populates="products")
    items: Mapped[list["Item"]] = relationship(back_populates="product", cascade="all, delete-orphan")

class Item(Base):
    """Штучные товары (аккаунты, ключи, промокоды) для автовыдачи"""
    __tablename__ = "items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    data: Mapped[str] = mapped_column(Text)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    product: Mapped["Product"] = relationship(back_populates="items")

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_code: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    product_id: Mapped[int] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String(150))
    amount: Mapped[float] = mapped_column(Float)
    payment_method: Mapped[str] = mapped_column(String(32))  # "balance", "stars", "cryptobot", "sbp"
    delivered_data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PromoCode(Base):
    __tablename__ = "promo_codes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    reward_amount: Mapped[float] = mapped_column(Float)
    max_activations: Mapped[int] = mapped_column(Integer, default=1)
    activated_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PromoActivation(Base):
    __tablename__ = "promo_activations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promo_id: Mapped[int] = mapped_column(Integer, ForeignKey("promo_codes.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger)
    activated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PaymentInvoice(Base):
    __tablename__ = "payment_invoices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_code: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    amount_rub: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(32))  # "stars", "cryptobot", "sbp_manual"
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending", "paid", "rejected"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
