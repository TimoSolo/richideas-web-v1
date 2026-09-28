/* Rich Ideas: forms, newsletter, scheduler and analytics glue. No dependencies. */
(function () {
  "use strict";
  var cfg = window.RI_CONFIG || {};

  /* ---- Analytics (only when configured) ---- */
  if (cfg.ga4) {
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(cfg.ga4);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", cfg.ga4, { anonymize_ip: true });
  }
  function track(name, params) {
    if (window.gtag) { window.gtag("event", name, params || {}); }
  }

  /* ---- Footer year ---- */
  Array.prototype.forEach.call(document.querySelectorAll("[data-ri-year]"), function (el) {
    el.textContent = String(new Date().getFullYear());
  });

  /* ---- Scheduler button on the booking page ---- */
  if (cfg.bookingUrl) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-ri-scheduler]"), function (el) {
      var a = el.querySelector("[data-ri-scheduler-link]");
      if (a) { a.href = cfg.bookingUrl; }
      el.hidden = false;
    });
  }

  /* ---- Newsletter (Substack subscribe page, pre-filled) ---- */
  Array.prototype.forEach.call(document.querySelectorAll("[data-ri-newsletter]"), function (form) {
    form.addEventListener("submit", function () { track("newsletter_signup", { location: form.closest("footer, section, div") ? "site" : "page" }); });
  });

  /* ---- Forms ---- */
  function serialize(form) {
    var data = {}, order = [];
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.name === "_gotcha" || el.disabled) { return; }
      if ((el.type === "checkbox" || el.type === "radio") && !el.checked) { return; }
      if (el.type === "submit" || el.type === "button") { return; }
      var v = el.value.trim();
      if (!v) { return; }
      if (data[el.name] === undefined) { data[el.name] = v; order.push(el.name); }
      else { data[el.name] += ", " + v; }
    });
    return { data: data, order: order };
  }

  function show(form, which) {
    Array.prototype.forEach.call(form.querySelectorAll(".ri-msg"), function (m) { m.hidden = true; });
    var el = form.querySelector(".ri-msg--" + which);
    if (el) { el.hidden = false; el.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  }

  function validate(form) {
    var ok = true, first = null;
    Array.prototype.forEach.call(form.querySelectorAll("input, select, textarea"), function (el) {
      var field = el.closest(".ri-field, .ri-rating") || el;
      var valid = el.checkValidity();
      if (el.type === "radio" && el.required) {
        valid = !!form.querySelector('input[name="' + el.name + '"]:checked');
      }
      field.classList.toggle("ri-invalid", !valid);
      if (!valid) { ok = false; first = first || el; }
    });
    if (first) { first.focus(); }
    return ok;
  }

  function mailtoFallback(form, subject, ser) {
    var lines = ser.order.map(function (k) { return k + ": " + ser.data[k]; });
    lines.push("", "Sent from " + location.href);
    var href = "mailto:" + encodeURIComponent(cfg.formEmail || "hello@richideas.co.za") +
      "?subject=" + encodeURIComponent(subject) +
      "&body=" + encodeURIComponent(lines.join("\n"));
    show(form, "mail");
    window.location.href = href;
  }

  function post(form, subject, ser, button) {
    var payload = Object.assign({}, ser.data, {
      subject: subject,
      form: form.getAttribute("data-ri-form"),
      page: location.href,
      replyto: ser.data.Email || ser.data["Email address"] || ""
    });
    if (cfg.formAccessKey) { payload.access_key = cfg.formAccessKey; }
    button.disabled = true;
    var label = button.textContent;
    button.textContent = "Sending…";
    return fetch(cfg.formEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      form.reset();
      show(form, "ok");
      track("form_submit", { form: payload.form });
    }).catch(function () {
      show(form, "err");
    }).then(function () {
      button.disabled = false;
      button.textContent = label;
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll("form[data-ri-form]"), function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var hp = form.querySelector('[name="_gotcha"]');
      if (hp && hp.value) { return; } /* bot */
      if (!validate(form)) { return; }
      var subject = form.getAttribute("data-subject") || "Website enquiry";
      var ser = serialize(form);
      var button = form.querySelector(".ri-submit");
      if (cfg.formEndpoint) { post(form, subject, ser, button); }
      else { mailtoFallback(form, subject, ser); track("form_submit", { form: form.getAttribute("data-ri-form"), mode: "mailto" }); }
    });
    Array.prototype.forEach.call(form.querySelectorAll("input, select, textarea"), function (el) {
      el.addEventListener("input", function () {
        var field = el.closest(".ri-field, .ri-rating");
        if (field && el.checkValidity()) { field.classList.remove("ri-invalid"); }
      });
    });
  });
})();
