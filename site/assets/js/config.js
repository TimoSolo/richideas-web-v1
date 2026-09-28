/* Rich Ideas site configuration.
 * Everything that connects the static site to an outside service lives here,
 * so it can be switched on without touching any page.
 */
window.RI_CONFIG = {
  /* Where form submissions are POSTed. Leave empty to keep forms
   * "unconnected": the visitor's email app opens with the details filled in.
   * Works with Web3Forms ("https://api.web3forms.com/submit" + formAccessKey),
   * Formspree ("https://formspree.io/f/XXXX") or your own endpoint. */
  formEndpoint: "",
  formAccessKey: "",

  /* Address used for the email fallback and the reply-to of submissions. */
  formEmail: "hello@richideas.co.za",

  /* Optional online scheduler (cal.com, Calendly...). When set, the booking
   * page shows a "choose a slot" button above the request form. */
  bookingUrl: "",

  /* Google Analytics 4 measurement id, e.g. "G-XXXXXXXXXX". Empty = off. */
  ga4: ""
};
