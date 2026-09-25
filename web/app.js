(() => {
  "use strict";

  const PROVIDER_LABELS = { aws: "AWS", azure: "Azure", gcp: "GCP" };
  const PRODUCT_LABELS = { "vm-series": "VM-Series", panorama: "Panorama", airs: "Prisma AIRS" };
  const LICENCE_LABELS = { byol: "BYOL", bundle1: "PAYG Bundle 1", bundle2: "PAYG Bundle 2", bundle3: "PAYG Bundle 3" };
  const PRODUCT_ORDER = ["vm-series", "panorama", "airs"];
  const LICENCE_ORDER = ["byol", "bundle1", "bundle2", "bundle3"];

  const state = { search: "", provider: "", product: "", licence: "", hideEol: false, expanded: new Set() };
  let records = [];

  const el = (id) => document.getElementById(id);
  const today = () => new Date().toISOString().slice(0, 10);

  function recordKey(r) {
    return [r.provider, r.version, r.product, r.licence].join(":");
  }

  function searchText(r) {
    const parts = [
      r.version, r.train, r.product, r.licence, r.provider,
      r.product_code, r.offer, r.sku, r.image_version, r.image_name, r.cpu,
      r.eol ? "eol end-of-life" : "supported current",
    ];
    if (r.amis) {
      parts.push(Object.keys(r.amis).join(" "));
      parts.push(Object.values(r.amis).join(" "));
    }
    return parts.filter(Boolean).join(" ").toLowerCase();
  }

  function compareVersion(a, b) {
    return (
      (b.major - a.major) ||
      (b.minor - a.minor) ||
      (b.patch - a.patch) ||
      ((b.hotfix || 0) - (a.hotfix || 0)) ||
      a.provider.localeCompare(b.provider) ||
      a.product.localeCompare(b.product) ||
      a.licence.localeCompare(b.licence)
    );
  }

  function buildChips(containerId, options, labels, key) {
    const container = el(containerId);
    const all = document.createElement("button");
    all.className = "chip active";
    all.textContent = "All";
    all.dataset.value = "";
    container.appendChild(all);
    for (const value of options) {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = labels[value];
      btn.dataset.value = value;
      container.appendChild(btn);
    }
    container.addEventListener("click", (e) => {
      const btn = e.target.closest(".chip");
      if (!btn) return;
      state[key] = btn.dataset.value;
      [...container.children].forEach((c) => c.classList.toggle("active", c === btn));
      render();
    });
  }

  function badge(r) {
    if (r.eol === true) {
      if (r.eol_extended_date && r.eol_extended_date >= today()) {
        return `<span class="badge eol-extended">EOL, extended to ${r.eol_extended_date}</span>`;
      }
      return `<span class="badge eol">EOL</span>`;
    }
    if (r.eol === null || r.eol === undefined) {
      return `<span class="badge unknown">EOL unknown</span>`;
    }
    return "";
  }

  function detailHtml(r) {
    const fields = [];
    fields.push(["EOL date", r.eol_date || "unknown"]);
    if (r.eol_extended_date) fields.push(["Extended support to", r.eol_extended_date]);

    if (r.provider === "aws") {
      fields.push(["Product code", r.product_code]);
      const regionCount = r.amis ? Object.keys(r.amis).length : 0;
      const grid = r.amis
        ? Object.keys(r.amis).sort().map((region) =>
            `<div><span class="k">${region}</span>${r.amis[region]}</div>`
          ).join("")
        : "";
      return `
        <p class="detail-fields">${fields.map(([k, v]) => `<span class="k">${k}</span><span class="v">${v}</span>`).join("")}</p>
        <p class="meta">${regionCount} region${regionCount === 1 ? "" : "s"}</p>
        <div class="detail-grid">${grid}</div>
      `;
    }

    if (r.provider === "azure") {
      fields.push(["CPU", r.cpu], ["Offer", r.offer], ["SKU", r.sku], ["Image version (deploy with this)", r.image_version]);
    } else if (r.provider === "gcp") {
      fields.push(["CPU", r.cpu], ["Image name (deploy with this)", r.image_name]);
    }

    return `<p class="detail-fields">${fields
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => `<span class="k">${k}</span><span class="v">${v}</span>`)
      .join("")}</p>`;
  }

  function filtered() {
    const term = state.search.trim().toLowerCase();
    return records.filter((r) => {
      if (state.provider && r.provider !== state.provider) return false;
      if (state.product && r.product !== state.product) return false;
      if (state.licence && r.licence !== state.licence) return false;
      if (state.hideEol && r.eol === true) return false;
      if (term && !r._search.includes(term)) return false;
      return true;
    });
  }

  function render() {
    const rows = filtered().sort(compareVersion);
    el("count").textContent = `${rows.length} of ${records.length} images`;
    el("empty").hidden = rows.length !== 0;

    const tbody = el("rows");
    tbody.innerHTML = "";
    const frag = document.createDocumentFragment();

    for (const r of rows) {
      const key = recordKey(r);
      const tr = document.createElement("tr");
      tr.className = "record" + (state.expanded.has(key) ? " open" : "");
      tr.dataset.key = key;
      tr.innerHTML = `
        <td><span class="chevron">+</span></td>
        <td class="version">${r.version}</td>
        <td>${r.train}</td>
        <td>${PRODUCT_LABELS[r.product] || r.product}</td>
        <td>${LICENCE_LABELS[r.licence] || r.licence}</td>
        <td>${PROVIDER_LABELS[r.provider] || r.provider}</td>
        <td>${badge(r)}</td>
      `;
      frag.appendChild(tr);

      if (state.expanded.has(key)) {
        const detail = document.createElement("tr");
        detail.className = "detail-row";
        const td = document.createElement("td");
        td.colSpan = 7;
        td.innerHTML = detailHtml(r);
        detail.appendChild(td);
        frag.appendChild(detail);
      }
    }
    tbody.appendChild(frag);
  }

  function init(data) {
    records = data.images.map((r) => ({ ...r, _search: "" }));
    records.forEach((r) => { r._search = searchText(r); });

    el("generated").textContent = `Data generated ${data.generated}`;

    buildChips("provider-chips", ["aws", "azure", "gcp"], PROVIDER_LABELS, "provider");
    buildChips("product-chips", PRODUCT_ORDER, PRODUCT_LABELS, "product");

    const select = el("licence-select");
    for (const l of LICENCE_ORDER) {
      const opt = document.createElement("option");
      opt.value = l;
      opt.textContent = LICENCE_LABELS[l];
      select.appendChild(opt);
    }
    select.addEventListener("change", () => { state.licence = select.value; render(); });

    let debounce;
    el("search").addEventListener("input", (e) => {
      clearTimeout(debounce);
      const value = e.target.value;
      debounce = setTimeout(() => { state.search = value; render(); }, 120);
    });

    el("hide-eol").addEventListener("change", (e) => { state.hideEol = e.target.checked; render(); });

    el("rows").addEventListener("click", (e) => {
      const tr = e.target.closest("tr.record");
      if (!tr) return;
      const key = tr.dataset.key;
      if (state.expanded.has(key)) state.expanded.delete(key);
      else state.expanded.add(key);
      render();
    });

    render();
  }

  fetch("data/versions.json")
    .then((res) => res.json())
    .then(init)
    .catch((err) => {
      el("generated").textContent = "Failed to load data/versions.json";
      console.error(err);
    });
})();
