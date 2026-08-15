(function () {
    function showSection(id) {
        const section = document.getElementById(id);
        const control = document.querySelector(`.control[data-id="${id}"]`);
        if (!section || !control) return;
        document.querySelector(".active-btn").classList.remove("active-btn");
        control.classList.add("active-btn");
        document.querySelector(".active").classList.remove("active");
        section.classList.add("active");
    }

    [...document.querySelectorAll(".control")].forEach(button => {
        button.addEventListener("click", () => showSection(button.dataset.id));
    });

    [...document.querySelectorAll("[data-nav]")].forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            showSection(link.dataset.nav);
        });
    });
    // Guarded because an unguarded querySelector that returns null throws here and takes the
    // rest of this file down with it. That is not hypothetical: the contact form's submit
    // handler was wired on the line below this one, and removing the form without removing
    // the listener would have thrown on every page load.
    const themeBtn = document.querySelector(".theme-btn");
    if (themeBtn) {
        themeBtn.addEventListener("click", () => {
            document.body.classList.toggle("light-mode");
        });
    }
})();