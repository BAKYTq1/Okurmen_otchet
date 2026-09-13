/* ─────────────────────────────────────────────────────────────────────────
   Конфигурация
   ───────────────────────────────────────────────────────────────────────── */
const BOT_TOKEN = "8377802582:AAGWC4wmDww1gA6nuPnZ9ZRoBWdOFLH1D0k";
const ADMIN_ID  = "1455437534";

const RATING_LABELS = {
  1: "😞 Плохо",
  2: "😐 Ниже среднего",
  3: "🙂 Нормально",
  4: "😊 Хорошо",
  5: "🤩 Отлично!",
};

/* ─────────────────────────────────────────────────────────────────────────
   DOM-элементы
   ───────────────────────────────────────────────────────────────────────── */
const form          = document.getElementById("reviewForm");
const formCard      = document.getElementById("formCard");
const successScreen = document.getElementById("successScreen");
const btnAgain      = document.getElementById("btnAgain");
const submitBtn     = document.getElementById("submitBtn");
const btnSpinner    = document.getElementById("btnSpinner");

const fullNameInput = document.getElementById("fullName");
const mentorSelect  = document.getElementById("mentor");
const reviewText    = document.getElementById("reviewText");
const ratingInput   = document.getElementById("ratingValue");
const ratingLabel   = document.getElementById("ratingLabel");
const charCount     = document.getElementById("charCount");

const stars         = document.querySelectorAll(".star");

/* ─────────────────────────────────────────────────────────────────────────
   Звёздный рейтинг
   ───────────────────────────────────────────────────────────────────────── */
function setStars(value) {
  stars.forEach(star => {
    const v = parseInt(star.dataset.value);
    star.classList.toggle("active", v <= value);
  });
  ratingInput.value   = value;
  ratingLabel.textContent = RATING_LABELS[value] ?? "Нажмите на звезду";
}

stars.forEach(star => {
  star.addEventListener("click", () => {
    setStars(parseInt(star.dataset.value));
    clearError("ratingError", ratingInput);
  });

  // Подсветка при наведении
  star.addEventListener("mouseenter", () => {
    const v = parseInt(star.dataset.value);
    stars.forEach(s => s.classList.toggle("active", parseInt(s.dataset.value) <= v));
  });
  star.addEventListener("mouseleave", () => {
    const current = parseInt(ratingInput.value) || 0;
    stars.forEach(s => s.classList.toggle("active", parseInt(s.dataset.value) <= current));
  });
});

/* ─────────────────────────────────────────────────────────────────────────
   Счётчик символов
   ───────────────────────────────────────────────────────────────────────── */
reviewText.addEventListener("input", () => {
  const len = reviewText.value.length;
  charCount.textContent = len;
  if (len > 950) charCount.style.color = "#ef4444";
  else if (len > 800) charCount.style.color = "#fbbf24";
  else charCount.style.color = "";
  if (len > 1000) reviewText.value = reviewText.value.slice(0, 1000);
});

/* ─────────────────────────────────────────────────────────────────────────
   Валидация
   ───────────────────────────────────────────────────────────────────────── */
function showError(errorId, field, msg) {
  document.getElementById(errorId).textContent = msg;
  if (field) field.classList.add("is-invalid");
}
function clearError(errorId, field) {
  document.getElementById(errorId).textContent = "";
  if (field) field.classList.remove("is-invalid");
}

function validate() {
  let valid = true;

  // ФИО
  const name = fullNameInput.value.trim();
  if (name.split(/\s+/).filter(Boolean).length < 2) {
    showError("fullNameError", fullNameInput, "Введите полное ФИО (минимум имя и фамилия)");
    valid = false;
  } else {
    clearError("fullNameError", fullNameInput);
  }

  // Ментор
  if (!mentorSelect.value) {
    showError("mentorError", mentorSelect, "Выберите ментора из списка");
    valid = false;
  } else {
    clearError("mentorError", mentorSelect);
  }

  // Рейтинг
  if (!ratingInput.value) {
    showError("ratingError", null, "Поставьте оценку ментору");
    valid = false;
  } else {
    clearError("ratingError", null);
  }

  // Отзыв
  const review = reviewText.value.trim();
  if (review.length < 10) {
    showError("reviewError", reviewText, "Напишите отзыв (минимум 10 символов)");
    valid = false;
  } else {
    clearError("reviewError", reviewText);
  }

  return valid;
}

/* ─────────────────────────────────────────────────────────────────────────
   Отправка в Telegram
   ───────────────────────────────────────────────────────────────────────── */
async function sendToTelegram(name, mentor, rating, review) {
  const stars = "⭐".repeat(rating);

  const text =
    `🔔 <b>Новый отзыв с сайта!</b>\n\n` +
    `👤 <b>Студент:</b> ${escapeHtml(name)}\n` +
    `👨‍🏫 <b>Ментор:</b> ${escapeHtml(mentor)}\n` +
    `${stars} <b>Оценка:</b> ${rating}/5\n\n` +
    `💬 <b>Отзыв:</b>\n${escapeHtml(review)}`;

  const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id:    ADMIN_ID,
      text:       text,
      parse_mode: "HTML",
    }),
  });

  const result = await response.json();
  if (!result.ok) {
    throw new Error(result.description || "Telegram API error");
  }
  return result;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/* ─────────────────────────────────────────────────────────────────────────
   Обработка формы
   ───────────────────────────────────────────────────────────────────────── */
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!validate()) return;

  // Блокируем кнопку
  submitBtn.disabled = true;
  submitBtn.querySelector(".btn-text").textContent = "Отправляем...";
  btnSpinner.hidden = false;

  const name   = fullNameInput.value.trim();
  const mentor = mentorSelect.value;
  const rating = parseInt(ratingInput.value);
  const review = reviewText.value.trim();

  try {
    await sendToTelegram(name, mentor, rating, review);
    showSuccess();
  } catch (err) {
    console.error(err);
    alert("Не удалось отправить отзыв. Проверьте подключение к интернету и попробуйте ещё раз.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.querySelector(".btn-text").textContent = "Отправить отзыв";
    btnSpinner.hidden = true;
  }
});

/* ─────────────────────────────────────────────────────────────────────────
   Экран успеха / сброс
   ───────────────────────────────────────────────────────────────────────── */
function showSuccess() {
  formCard.hidden      = true;
  successScreen.hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

btnAgain.addEventListener("click", () => {
  form.reset();
  charCount.textContent = "0";
  ratingInput.value     = "";
  ratingLabel.textContent = "Нажмите на звезду";
  stars.forEach(s => s.classList.remove("active"));
  ["fullNameError","mentorError","ratingError","reviewError"].forEach(id => {
    document.getElementById(id).textContent = "";
  });
  [fullNameInput, mentorSelect, reviewText].forEach(el => el.classList.remove("is-invalid"));

  successScreen.hidden = false;
  formCard.hidden      = true;

  successScreen.hidden = true;
  formCard.hidden      = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

/* ─────────────────────────────────────────────────────────────────────────
   Очистка ошибок при вводе
   ───────────────────────────────────────────────────────────────────────── */
fullNameInput.addEventListener("input", () => clearError("fullNameError", fullNameInput));
mentorSelect.addEventListener("change", () => clearError("mentorError", mentorSelect));
reviewText.addEventListener("input",   () => clearError("reviewError", reviewText));
