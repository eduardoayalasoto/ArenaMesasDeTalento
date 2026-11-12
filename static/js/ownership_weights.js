// Total en vivo de pesos de Ownership (spec 008). Se carga en el editor de cuestionarios.
// Décimas enteras para sumar sin errores de coma flotante: el grupo es válido solo si suma 1000 (100.0%).
document.addEventListener('alpine:init', () => {
  Alpine.store('weights', {
    invalid: {},
    get blocked() { return Object.values(this.invalid).some(Boolean); },
  });
  Alpine.data('weightGroup', (gid, initial) => ({
    gid,
    vals: initial,
    parse(v) {
      const s = String(v ?? '').trim().replace(',', '.');
      if (!/^\d{1,3}(\.\d)?$/.test(s)) return null;
      const t = Math.round(parseFloat(s) * 10);
      return t > 1000 ? null : t;
    },
    get hasInvalid() { return this.vals.some(v => this.parse(v) === null); },
    get total() { return this.vals.reduce((a, v) => a + (this.parse(v) ?? 0), 0); },
    get ok() { return this.vals.length > 0 && !this.hasInvalid && this.total === 1000; },
    get totalLabel() { return (this.total / 10).toFixed(1); },
    get gapLabel() {
      const gap = Math.abs(1000 - this.total) / 10;
      return this.total < 1000 ? `faltan ${gap.toFixed(1)}%` : `sobran ${gap.toFixed(1)}%`;
    },
    init() {
      this.$store.weights.invalid[this.gid] = !this.ok;
      this.$watch('ok', v => { this.$store.weights.invalid[this.gid] = !v; });
    },
    equalize() {
      const n = this.vals.length;
      if (!n) return;
      const base = Math.floor(1000 / n), extra = 1000 % n;
      this.vals = this.vals.map((_, i) => ((base + (i < extra ? 1 : 0)) / 10).toFixed(1));
    },
  }));
});
