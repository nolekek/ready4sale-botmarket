// ========================================================
// AutoShop Pro — Telegram Mini App Core JavaScript
// ========================================================

const tg = window.Telegram?.WebApp;

// Состояние приложения
const state = {
  shopName: "Digital Hub Shop",
  starRate: 2.0,
  user: {
    id: 953527769,
    first_name: "Пользователь",
    username: "",
    balance: 0.0,
    referrals: 0
  },
  categories: [],
  products: [],
  selectedCategory: "all",
  searchQuery: "",
  activeProduct: null,
  depositAmount: 250
};

// Инициализация Telegram WebApp
function initTelegram() {
  if (tg) {
    tg.ready();
    tg.expand();
    if (tg.enableClosingConfirmation) {
      tg.enableClosingConfirmation();
    }
    
    // Получение данных пользователя из Telegram
    if (tg.initDataUnsafe?.user) {
      const u = tg.initDataUnsafe.user;
      state.user.id = u.id;
      state.user.first_name = u.first_name || "Пользователь";
      state.user.username = u.username || "";
    }

    // Применение цветов темы Telegram
    document.body.classList.add("telegram-theme");
  }
}

// Вибрация / Тактильный отклик (Haptic Feedback)
function haptic(type = "light") {
  if (tg?.HapticFeedback) {
    if (type === "success") {
      tg.HapticFeedback.notificationOccurred("success");
    } else if (type === "error") {
      tg.HapticFeedback.notificationOccurred("error");
    } else if (type === "medium") {
      tg.HapticFeedback.impactOccurred("medium");
    } else {
      tg.HapticFeedback.impactOccurred("light");
    }
  }
}

// Уведомление Toast
function showToast(text, duration = 2500) {
  const toast = document.getElementById("toast");
  toast.innerText = text;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), duration);
}

// Загрузка данных магазина с API
async function loadAppData() {
  try {
    const initDataQuery = tg?.initData || "";
    const res = await fetch(`/api/init?user_id=${state.user.id}&init_data=${encodeURIComponent(initDataQuery)}`);
    if (res.ok) {
      const data = await res.json();
      state.shopName = data.shop_name || state.shopName;
      state.starRate = data.star_rate || state.starRate;
      if (data.user) {
        state.user.balance = data.user.balance || 0.0;
        state.user.referrals = data.user.referrals || 0;
        if (data.user.full_name) state.user.first_name = data.user.full_name;
      }
      state.categories = data.categories || [];
      state.products = data.products || [];
      
      updateUI();
      return;
    }
  } catch (err) {
    console.warn("API offline or running in mock preview mode:", err);
  }

  // Fallback demo mock если открыто локально в браузере без сервера
  state.categories = [
    { id: 1, name: "🎮 Игры и Ключи" },
    { id: 2, name: "🌐 VPN и Прокси" },
    { id: 3, name: "⭐ Stars & Подписки" }
  ];
  state.products = [
    {
      id: 1,
      category_id: 1,
      category_name: "🎮 Игры и Ключи",
      name: "Steam Random Key",
      description: "Лицензионный ключ для активации популярной игры в Steam с гарантией.",
      price: 99.0,
      product_type: "unique",
      stock: 3
    },
    {
      id: 2,
      category_id: 2,
      category_name: "🌐 VPN и Прокси",
      name: "Outline VPN (30 дней)",
      description: "Высокоскоростной защищенный VPN без лимитов трафика. Работает в РФ.",
      price: 149.0,
      product_type: "infinite",
      stock: 999
    },
    {
      id: 3,
      category_id: 3,
      category_name: "⭐ Stars & Подписки",
      name: "Telegram Stars 100 ⭐️",
      description: "Официальное пополнение 100 Telegram Stars по юзернейму за 1 минуту.",
      price: 190.0,
      product_type: "infinite",
      stock: 999
    }
  ];
  updateUI();
}

// Обновление интерфейса
function updateUI() {
  document.getElementById("shopName").innerText = state.shopName;
  
  // Профиль в шапке
  const avatarChar = (state.user.first_name || "U")[0].toUpperCase();
  document.getElementById("userAvatar").innerText = avatarChar;
  document.getElementById("userName").innerText = state.user.first_name;
  document.getElementById("userBalance").innerText = state.user.balance.toFixed(2);
  
  // Большой профиль
  document.getElementById("pAvatarBig").innerText = avatarChar;
  document.getElementById("pNameBig").innerText = state.user.first_name;
  document.getElementById("pIdBig").innerText = `ID: ${state.user.id}`;
  document.getElementById("pBalanceBig").innerText = `${state.user.balance.toFixed(2)} ₽`;
  document.getElementById("pReferralsBig").innerText = `${state.user.referrals} чел.`;

  renderCategories();
  renderProducts();
}

// Отрисовка чипсов категорий
function renderCategories() {
  const container = document.getElementById("categoriesBar");
  container.innerHTML = `
    <button class="cat-chip ${state.selectedCategory === 'all' ? 'active' : ''}" data-cat="all" onclick="selectCategory('all', this)">
      <span>🔥</span> Все товары
    </button>
  `;

  state.categories.forEach(cat => {
    const btn = document.createElement("button");
    btn.className = `cat-chip ${state.selectedCategory == cat.id ? 'active' : ''}`;
    btn.onclick = () => selectCategory(cat.id, btn);
    btn.innerHTML = `<span>📁</span> ${cat.name}`;
    container.appendChild(btn);
  });
}

// Выбор категории
function selectCategory(catId, btnElement) {
  haptic("light");
  state.selectedCategory = catId;
  document.querySelectorAll(".cat-chip").forEach(c => c.classList.remove("active"));
  if (btnElement) btnElement.classList.add("active");
  renderProducts();
}

// Поиск
function handleSearch(query) {
  state.searchQuery = query.trim().toLowerCase();
  const clearBtn = document.getElementById("clearSearchBtn");
  clearBtn.style.display = state.searchQuery ? "flex" : "none";
  renderProducts();
}

function clearSearch() {
  haptic("light");
  const input = document.getElementById("searchInput");
  input.value = "";
  handleSearch("");
}

// Отрисовка сетки товаров
function renderProducts() {
  const grid = document.getElementById("productsGrid");
  const emptyState = document.getElementById("emptyState");
  const countBadge = document.getElementById("itemsCountBadge");

  let filtered = state.products.filter(p => {
    const matchCat = state.selectedCategory === "all" || p.category_id == state.selectedCategory;
    const matchSearch = !state.searchQuery || 
      p.name.toLowerCase().includes(state.searchQuery) || 
      (p.description && p.description.toLowerCase().includes(state.searchQuery));
    return matchCat && matchSearch;
  });

  countBadge.innerText = `${filtered.length} поз.`;

  if (filtered.length === 0) {
    grid.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  grid.innerHTML = "";

  filtered.forEach(p => {
    const starsPrice = Math.max(1, Math.round(p.price / state.starRate));
    const isInfinite = p.product_type === "infinite";
    const inStock = isInfinite || p.stock > 0;
    const stockText = isInfinite ? "В наличии" : (p.stock > 0 ? `${p.stock} шт.` : "Нет на складе");
    const badgeText = isInfinite ? "⚡ Безлимит" : "🔑 Ключ / Аккаунт";

    // Иконка категории
    let icon = "📦";
    if (p.name.toLowerCase().includes("steam") || p.name.toLowerCase().includes("ключ")) icon = "🎮";
    if (p.name.toLowerCase().includes("vpn") || p.name.toLowerCase().includes("прокси")) icon = "🌐";
    if (p.name.toLowerCase().includes("star")) icon = "⭐";

    const card = document.createElement("div");
    card.className = "product-card";
    card.onclick = () => openProductModal(p);

    card.innerHTML = `
      <div class="card-top">
        <span class="item-badge ${isInfinite ? 'infinite' : ''}">${badgeText}</span>
        <span class="stock-tag ${inStock ? 'in-stock' : ''}">${stockText}</span>
      </div>
      <div class="card-icon">${icon}</div>
      <div class="product-name">${p.name}</div>
      <div class="product-desc-short">${p.description || "Мгновенная выдача после оплаты"}</div>
      <div class="card-bottom">
        <div class="price-box">
          <span class="price-main">${p.price.toFixed(0)} ₽</span>
          <span class="price-sub">⭐ ${starsPrice}</span>
        </div>
        <button class="card-buy-btn" title="Подробнее">➔</button>
      </div>
    `;

    grid.appendChild(card);
  });
}

// ================= МОДАЛКА ДЕТАЛЕЙ ТОВАРА =================
function openProductModal(product) {
  haptic("medium");
  state.activeProduct = product;

  document.getElementById("mProductCategory").innerText = product.category_name || "Товар";
  document.getElementById("mProductTitle").innerText = product.name;
  document.getElementById("mProductPrice").innerText = `${product.price.toFixed(0)} ₽`;
  
  const starsPrice = Math.max(1, Math.round(product.price / state.starRate));
  document.getElementById("mProductStars").innerText = `⭐ ${starsPrice}`;
  
  const isInfinite = product.product_type === "infinite";
  const stockText = isInfinite ? "В наличии (много)" : (product.stock > 0 ? `В наличии: ${product.stock} шт.` : "Нет в наличии");
  document.getElementById("mProductStock").innerText = stockText;
  
  document.getElementById("mProductDesc").innerText = product.description || "Мгновенная автовыдача сразу после покупки.";

  const buyBtn = document.getElementById("buyBtn");
  if (!isInfinite && product.stock <= 0) {
    buyBtn.disabled = true;
    buyBtn.innerText = "Товар закончился";
    buyBtn.style.opacity = "0.5";
  } else {
    buyBtn.disabled = false;
    buyBtn.innerHTML = `<span>Купить с баланса</span> <span class="btn-price-tag" id="buyBtnPrice">${product.price.toFixed(0)} ₽</span>`;
    buyBtn.style.opacity = "1";
  }

  document.getElementById("productModal").classList.add("open");
}

function closeProductModal(event) {
  haptic("light");
  document.getElementById("productModal").classList.remove("open");
}

// Покупка товара
async function handleBuyClick() {
  const p = state.activeProduct;
  if (!p) return;

  if (state.user.balance < p.price) {
    haptic("error");
    const needed = (p.price - state.user.balance).toFixed(0);
    closeProductModal();
    openDepositModal();
    showToast(`Недостаточно средств. Пополните на ${needed} ₽`);
    return;
  }

  haptic("medium");
  const buyBtn = document.getElementById("buyBtn");
  buyBtn.disabled = true;
  buyBtn.innerText = "Оформление заказа...";

  try {
    const res = await fetch("/api/buy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.user.id,
        product_id: p.id
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (data.ok) {
        haptic("success");
        state.user.balance = data.new_balance;
        updateUI();

        // Уменьшаем локальный остаток
        if (p.product_type === "unique") {
          p.stock = Math.max(0, p.stock - 1);
          renderProducts();
        }

        closeProductModal();
        openSuccessModal(data.order_code, data.delivered_data);
        return;
      } else {
        showToast(data.error || "Ошибка при покупке");
      }
    }
  } catch (err) {
    // Демонстрационный режим если бэкенд не доступен
    haptic("success");
    state.user.balance -= p.price;
    updateUI();
    closeProductModal();
    openSuccessModal("ORD-" + Math.random().toString(36).substring(2, 8).toUpperCase(), "DEMO-KEY-1111-2222-3333");
    return;
  }

  buyBtn.disabled = false;
  buyBtn.innerHTML = `<span>Купить с баланса</span> <span class="btn-price-tag" id="buyBtnPrice">${p.price.toFixed(0)} ₽</span>`;
}

// Модалка успешной автовыдачи
function openSuccessModal(orderCode, deliveredData) {
  document.getElementById("successOrderInfo").innerText = `Заказ #${orderCode}`;
  document.getElementById("deliveryContent").innerText = deliveredData;
  document.getElementById("successModal").classList.add("open");
}

function closeSuccessModal() {
  haptic("light");
  document.getElementById("successModal").classList.remove("open");
}

function copyDeliveredData() {
  haptic("success");
  const text = document.getElementById("deliveryContent").innerText;
  navigator.clipboard.writeText(text);
  const btn = document.getElementById("copyDeliveryBtn");
  btn.innerText = "✅ Скопировано!";
  setTimeout(() => btn.innerText = "📋 Скопировать данные", 2000);
  showToast("Данные скопированы в буфер обмена!");
}

// ================= ПОПОЛНЕНИЕ =================
function openDepositModal() {
  haptic("light");
  updateDepositCalc();
  document.getElementById("depositModal").classList.add("open");
}

function closeDepositModal() {
  document.getElementById("depositModal").classList.remove("open");
}

function setDepositAmount(amount) {
  haptic("light");
  state.depositAmount = amount;
  document.getElementById("customDepositInput").value = amount;
  document.querySelectorAll(".preset-btn").forEach(b => {
    b.classList.toggle("active", b.innerText.includes(amount));
  });
  updateDepositCalc();
}

function updateDepositCalc() {
  const val = parseFloat(document.getElementById("customDepositInput").value) || 0;
  state.depositAmount = val;
  const stars = Math.max(1, Math.round(val / state.starRate));
  document.getElementById("starsCalcBadge").innerText = `~${stars} ⭐️`;
}

function startPayment(method) {
  haptic("medium");
  const amount = state.depositAmount;
  if (amount < 10) {
    showToast("Минимальная сумма пополнения — 10 ₽");
    return;
  }

  closeDepositModal();

  if (tg) {
    // Отправляем команду в чат Telegram для генерации счета
    tg.sendData(JSON.stringify({ action: "deposit", method: method, amount: amount }));
    tg.close();
  } else {
    showToast(`Запрос на оплату ${amount} ₽ через ${method} отправлен.`);
  }
}

// ================= ПРОМОКОД =================
function openPromoModal() {
  haptic("light");
  document.getElementById("promoInput").value = "";
  document.getElementById("promoResult").style.display = "none";
  document.getElementById("promoModal").classList.add("open");
}

function closePromoModal() {
  document.getElementById("promoModal").classList.remove("open");
}

async function submitPromoCode() {
  const code = document.getElementById("promoInput").value.trim().toUpperCase();
  if (!code) {
    showToast("Введите промокод");
    return;
  }

  haptic("medium");
  const btn = document.getElementById("activatePromoBtn");
  btn.disabled = true;
  btn.innerText = "Проверка...";

  const alertBox = document.getElementById("promoResult");

  try {
    const res = await fetch("/api/promo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: state.user.id, code: code })
    });

    if (res.ok) {
      const data = await res.json();
      alertBox.style.display = "block";
      if (data.ok) {
        haptic("success");
        alertBox.className = "promo-alert success";
        alertBox.innerText = data.message;
        state.user.balance = data.new_balance;
        updateUI();
        setTimeout(() => closePromoModal(), 1800);
      } else {
        haptic("error");
        alertBox.className = "promo-alert error";
        alertBox.innerText = data.error;
      }
    }
  } catch (err) {
    // Демо-тест
    if (code === "TEST100") {
      haptic("success");
      alertBox.style.display = "block";
      alertBox.className = "promo-alert success";
      alertBox.innerText = "✅ Промокод активирован! +100.0 ₽";
      state.user.balance += 100;
      updateUI();
      setTimeout(() => closePromoModal(), 1500);
    } else {
      haptic("error");
      alertBox.style.display = "block";
      alertBox.className = "promo-alert error";
      alertBox.innerText = "❌ Промокод не найден.";
    }
  }

  btn.disabled = false;
  btn.innerText = "Активировать промокод";
}

// ================= ИСТОРИЯ ЗАКАЗОВ =================
async function openOrdersModal() {
  haptic("light");
  const list = document.getElementById("ordersList");
  list.innerHTML = "<p class='loading-text'>Загрузка заказов...</p>";
  document.getElementById("ordersModal").classList.add("open");

  try {
    const res = await fetch(`/api/orders?user_id=${state.user.id}`);
    if (res.ok) {
      const orders = await res.json();
      if (orders.length === 0) {
        list.innerHTML = "<p class='empty-state'>У вас пока нет оформленных заказов.</p>";
        return;
      }

      list.innerHTML = "";
      orders.forEach(o => {
        const item = document.createElement("div");
        item.className = "order-item-card";
        item.innerHTML = `
          <div class="order-top">
            <span class="order-code">#${o.order_code}</span>
            <span class="order-date">${o.created_at}</span>
          </div>
          <div class="order-product">${o.product_name} (${o.amount} ₽)</div>
          <div class="order-key">${o.delivered_data}</div>
        `;
        list.appendChild(item);
      });
      return;
    }
  } catch (err) {
    list.innerHTML = "<p class='empty-state'>История заказов пуста.</p>";
  }
}

function closeOrdersModal() {
  document.getElementById("ordersModal").classList.remove("open");
}

// ================= ПРОФИЛЬ =================
function openProfileModal() {
  haptic("light");
  document.getElementById("profileModal").classList.add("open");
}

function closeProfileModal() {
  document.getElementById("profileModal").classList.remove("open");
}

function copyRefLink() {
  haptic("success");
  const link = `https://t.me/${state.shopName}?start=ref_${state.user.id}`;
  navigator.clipboard.writeText(link);
  showToast("Реферальная ссылка скопирована!");
}

// Нижняя навигация
function switchNav(type) {
  haptic("light");
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  event.currentTarget.classList.add("active");
  if (type === "catalog") {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

// Запуск при загрузке страницы
document.addEventListener("DOMContentLoaded", () => {
  initTelegram();
  loadAppData();
});
