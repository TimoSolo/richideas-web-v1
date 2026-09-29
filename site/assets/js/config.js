/* Rich Ideas site configuration.
 * Everything that connects the static site to an outside service lives here,
 * so it can be switched on without touching any page.
 */
window.RI_CONFIG = {
  /* Where form submissions are POSTed. Leave empty to keep forms
   * "unconnected": the visitor's email app opens with the details filled in.
   * The shared seven forms relay: "https://forms.7vn.dev/richideas" (see the
   * 7vn.dev repo, workers/forms). Web3Forms ("https://api.web3forms.com/submit"
   * + formAccessKey) and Formspree also work. */
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
