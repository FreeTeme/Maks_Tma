document.addEventListener("DOMContentLoaded", () => {
    // Работа с вкладками
    const tabs = document.querySelectorAll(".tab");
    const tabContents = document.querySelectorAll(".tab-content");

    // Устанавливаем первую вкладку активной по умолчанию
    if (tabs.length > 0 && tabContents.length > 0) {
        tabs[0].classList.add("active");
        tabContents[0].classList.add("active");
    }

    // Переключение вкладок
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            // Сброс активного состояния для всех вкладок и контента
            tabs.forEach(t => t.classList.remove("active"));
            tabContents.forEach(content => content.classList.remove("active"));

            // Установка активного состояния для выбранной вкладки и контента
            tab.classList.add("active");
            const activeTabContent = document.getElementById(`${tab.dataset.tab}-content`);
            if (activeTabContent) {
                activeTabContent.classList.add("active");
            }
        });
    });

    // Работа с боковым меню
    const hamburgerMenu = document.querySelector(".hamburger-menu");
    const sideMenu = document.getElementById("side-menu");

    if (hamburgerMenu && sideMenu) {
        // Открытие и закрытие бокового меню
        hamburgerMenu.addEventListener("click", () => {
            sideMenu.classList.toggle("show");
        });
    }

    // Работа с панелью торговых настроек
    const tradingModePanel = document.getElementById("tradingModePanel");
    const tradingOptionsBlock = document.getElementById("tradingOptionsBlock");
    const closeButton = document.getElementById("closeButton");
    const balanceText = document.getElementById("balanceText");
    const radioButtons = document.querySelectorAll('input[name="tradeMode"]');

    if (tradingModePanel && tradingOptionsBlock) {
        // Показать блок настроек, выдвигая его снизу
        tradingModePanel.addEventListener("click", () => {
            tradingOptionsBlock.classList.toggle("show");
        });
    }

    if (closeButton && tradingOptionsBlock) {
        // Закрыть блок при нажатии кнопки "Закрыть"
        closeButton.addEventListener("click", () => {
            tradingOptionsBlock.classList.remove("show");
        });
    }

    if (radioButtons && balanceText) {
        // Обработчик для изменения текста баланса при выборе опции
        radioButtons.forEach(radio => {
            radio.addEventListener("change", () => {
                if (radio.checked) {
                    if (radio.value === "Game score") {
                        balanceText.innerHTML = '<i class="fa-solid fa-coins"></i> 5301.23'; // Исправлено использование HTML-кода
                    } else {
                        balanceText.textContent = "$15,392.75"; // Исходное значение
                    }
                    tradingOptionsBlock.classList.remove("show"); // Закрыть блок после выбора
                }
            });
        });
    }

    // Переходы между страницами
    const chartButton = document.getElementById('open-chart');
    if (chartButton) {
        chartButton.addEventListener('click', function () {
            window.location.href = '/chart';
        });
    }

    const glavButton = document.getElementById('open-glav');
    if (glavButton) {
        glavButton.addEventListener('click', function () {
            window.location.href = 'index1.html';
        });
    }

    const calkButton = document.getElementById('calk');
    if (calkButton) {
        calkButton.addEventListener('click', function () {
            window.location.href = 'calk.html';
        });
    }
});
