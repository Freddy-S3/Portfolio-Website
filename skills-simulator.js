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
        "The login button is broken and I have no idea why yet.",
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

    document.addEventListener("DOMContentLoaded", function () {
        if (!DATA.length) { return; }
        populateExamples();
        renderCatalog();
        document.getElementById("route-btn").addEventListener("click", function () {
            renderResult(document.getElementById("task-input").value);
        });
    });
})();
