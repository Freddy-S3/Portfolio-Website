(function () {
    var DATA = JSON.parse(document.getElementById("skills-data").textContent || "[]");
    var STOPWORDS = ["the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "when",
        "use", "uses", "using", "is", "are", "it", "this", "that", "as", "at", "by", "be", "into",
        "from", "not", "any", "one", "so", "than", "then", "will", "own", "its", "their", "your", "you"];

    var EXAMPLE_TASKS = [
        "Add a new checkout API endpoint to the ticket-backed billing service.",
        "Run the whole overnight data migration while I'm asleep, don't wait for me to check in.",
        "I hit my usage limit halfway through this queue item, will it pick back up on its own after the reset?",
        "Quick, is the PR from yesterday still waiting on my review?",
        "Review this pull request like a strict senior engineer would.",
        "Something in the login flow is throwing errors, help me investigate the unexpected behavior.",
        "Turn this rough plan into vertical-slice tracker tickets for the team.",
        "Draft a Confluence page documenting our new auth flow."
    ];

    function tokenize(text) {
        var words = (text.toLowerCase().match(/[a-z][a-z0-9'\-]{2,}/g)) || [];
        var seen = {};
        var out = [];
        words.forEach(function (w) {
            if (STOPWORDS.indexOf(w) !== -1 || seen[w]) { return; }
            seen[w] = true;
            out.push(w);
        });
        return out;
    }

    function detectMode(text) {
        var lower = text.toLowerCase();
        if (/ticket|jira|delivery|shared repo|production/.test(lower)) {
            return { command: "/freddy", label: "Delivery mode", reason: "mentions ticket-backed or shared-system work" };
        }
        if (/overnight|asleep|while i sleep|zero.interruption|no questions/.test(lower)) {
            return { command: "/sleep", label: "Sleep mode", reason: "unattended, overnight phrasing" };
        }
        if (/queue|backlog|usage limit|resume/.test(lower)) {
            return { command: "/queue", label: "Queue mode", reason: "backlog / resume-after-limit phrasing" };
        }
        return { command: "/faruk", label: "Personal mode (default)", reason: "no delivery, overnight, or queue signal detected" };
    }

    function routeTask(text) {
        var tokens = tokenize(text);
        var scored = DATA.map(function (skill) {
            var overlap = skill.keywords.filter(function (k) { return tokens.indexOf(k) !== -1; });
            return { skill: skill, score: overlap.length, matched: overlap };
        }).sort(function (a, b) { return b.score - a.score; });

        var mode = detectMode(text);
        return { top: scored[0], runnerUp: scored[1], mode: mode };
    }

    function esc(s) {
        var div = document.createElement("div");
        div.textContent = s;
        return div.innerHTML;
    }

    function renderResult(text) {
        var out = document.getElementById("simulator-result");
        if (!text || !text.trim()) {
            out.innerHTML = '<p class="result-placeholder">Pick or type a task, then hit "Route this task".</p>';
            return;
        }
        var routed = routeTask(text);
        var top = routed.top;
        if (!top || top.score === 0) {
            out.innerHTML =
                '<div class="result-card no-match">' +
                '<p class="result-command">No skill matched</p>' +
                '<p>None of the skill descriptions share enough vocabulary with this task &mdash; it would fall through to the ' +
                'default general-purpose agent rather than a named skill.</p>' +
                '<p class="result-mode"><span class="mode-pill">' + esc(routed.mode.label) + '</span> would still apply (' + esc(routed.mode.reason) + ').</p>' +
                "</div>";
            return;
        }
        var skill = top.skill;
        var badges = "";
        if (skill.userInvocable) { badges += '<span class="badge">user-invocable</span>'; }
        badges += skill.autoInvocable
            ? '<span class="badge">auto-triggers</span>'
            : '<span class="badge badge-muted">explicit call only</span>';

        var runnerUpHtml = "";
        if (routed.runnerUp && routed.runnerUp.score > 0) {
            runnerUpHtml = '<p class="result-runner-up">Runner-up: <code>' + esc(routed.runnerUp.skill.command) +
                "</code> (" + routed.runnerUp.score + " matching term" + (routed.runnerUp.score === 1 ? "" : "s") + ")</p>";
        }

        out.innerHTML =
            '<div class="result-card">' +
            '<p class="result-mode"><span class="mode-pill">' + esc(routed.mode.label) + '</span> &mdash; ' + esc(routed.mode.reason) + '</p>' +
            '<p class="result-command">' + esc(skill.command) + " " + badges + "</p>" +
            "<p>" + esc(skill.description) + "</p>" +
            '<p class="result-keywords">Matched on: ' + top.matched.map(function (k) { return "<code>" + esc(k) + "</code>"; }).join(" ") + "</p>" +
            runnerUpHtml +
            "</div>";
    }

    // ---------------------------------------------------------------- landing console
    // A trimmed router in the hero: one-tap examples, free text, and a compact verdict.
    // Same DATA and same routeTask() as the full simulator below - the landing view is a
    // second presentation of one engine, not a copy of it.

    var LANDING_CHIPS = [
        { label: "Ship a feature", task: EXAMPLE_TASKS[0] },
        { label: "Run it overnight", task: EXAMPLE_TASKS[1] },
        { label: "Review a PR", task: EXAMPLE_TASKS[4] },
        { label: "Debug something", task: EXAMPLE_TASKS[5] }
    ];

    function renderLandingResult(text) {
        var out = document.getElementById("lr-result");
        if (!out) { return; }
        var routed = routeTask(text);
        var top = routed.top;
        if (!top || top.score === 0) {
            out.innerHTML =
                '<div class="lr-card lr-no-match">' +
                '<p class="lr-command">No skill matched</p>' +
                "<p>Too little shared vocabulary with any skill description &mdash; this would fall " +
                "through to a general-purpose agent rather than a named skill.</p>" +
                "</div>";
            return;
        }
        // A single shared term is a coin-flip, not a routing decision, and saying so is
        // the honest reading of a keyword matcher. Hiding it would make the weakest
        // results look like the strongest ones.
        var weak = top.score < 2
            ? '<p class="lr-weak">Weak signal &mdash; only one shared term, so this is close to a guess.</p>'
            : "";

        out.innerHTML =
            '<div class="lr-card">' +
            '<p class="lr-mode"><span class="mode-pill">' + esc(routed.mode.label) + "</span></p>" +
            '<p class="lr-command">' + esc(top.skill.command) + "</p>" +
            '<p class="lr-desc">' + esc(top.skill.description) + "</p>" +
            '<p class="lr-keywords">Matched on ' +
            top.matched.slice(0, 4).map(function (k) { return "<code>" + esc(k) + "</code>"; }).join(" ") +
            "</p>" + weak +
            "</div>";
    }

    function routeFromLanding(text) {
        var input = document.getElementById("lr-input");
        if (input && input.value !== text) { input.value = text; }
        renderLandingResult(text);
    }

    function initLanding() {
        var chips = document.getElementById("lr-chips");
        var input = document.getElementById("lr-input");
        var button = document.getElementById("lr-btn");
        if (!chips || !input || !button) { return; }

        LANDING_CHIPS.forEach(function (chip, index) {
            var el = document.createElement("button");
            el.type = "button";
            el.className = "lr-chip";
            el.textContent = chip.label;
            el.title = chip.task;
            el.addEventListener("click", function () {
                [].forEach.call(chips.children, function (c) { c.classList.remove("is-active"); });
                el.classList.add("is-active");
                routeFromLanding(chip.task);
            });
            if (index === 0) { el.classList.add("is-active"); }
            chips.appendChild(el);
        });

        function routeTyped() {
            [].forEach.call(chips.children, function (c) { c.classList.remove("is-active"); });
            renderLandingResult(input.value);
        }
        button.addEventListener("click", routeTyped);
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") { event.preventDefault(); routeTyped(); }
        });

        // Show the system already working, so arriving is enough to see a routed result.
        routeFromLanding(LANDING_CHIPS[0].task);
    }

    function renderCatalog() {
        var el = document.getElementById("skill-catalog");
        el.innerHTML = DATA.map(function (skill) {
            var badges = "";
            if (skill.userInvocable) { badges += '<span class="badge">user-invocable</span>'; }
            badges += skill.autoInvocable
                ? '<span class="badge">auto-triggers</span>'
                : '<span class="badge badge-muted">explicit call only</span>';
            return (
                '<div class="skill-card">' +
                '<p class="skill-command">' + esc(skill.command) + "</p>" +
                "<p>" + esc(skill.description) + "</p>" +
                '<p class="skill-badges">' + badges + "</p>" +
                "</div>"
            );
        }).join("");
    }

    function renderSkillCount() {
        var el = document.getElementById("harness-skill-count");
        if (el) { el.textContent = DATA.length; }
    }

    function populateExamples() {
        var select = document.getElementById("task-select");
        var placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Choose an example...";
        select.appendChild(placeholder);
        EXAMPLE_TASKS.forEach(function (task) {
            var option = document.createElement("option");
            option.value = task;
            option.textContent = task;
            select.appendChild(option);
        });
        select.addEventListener("change", function () {
            if (select.value) {
                document.getElementById("task-input").value = select.value;
            }
        });
    }

    function whenIdle(fn) {
        if (typeof window.requestIdleCallback === "function") {
            window.requestIdleCallback(fn, { timeout: 1500 });
        } else {
            window.setTimeout(fn, 1);
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!DATA.length) { return; }
        // The landing console is the only thing a visitor can see on arrival, so it goes
        // first. The 33-card catalog sits inside a hidden section and costs a layout pass
        // nobody is waiting on, so it waits for idle rather than competing with first paint.
        initLanding();
        renderSkillCount();
        // Wiring is cheap and must not be racy - only the rendering waits.
        document.getElementById("route-btn").addEventListener("click", function () {
            renderResult(document.getElementById("task-input").value);
        });
        whenIdle(function () {
            populateExamples();
            renderCatalog();
        });
    });
})();
