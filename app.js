(function () {
    function submitForm() {
        document.getElementById('myForm').submit();
    }

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
    document.querySelector(".theme-btn").addEventListener("click", () => {
        document.body.classList.toggle("light-mode");
    })

    document.querySelector(".submit-btn a").addEventListener("click", submitForm);
})();