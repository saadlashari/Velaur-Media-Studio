/* The Velaur page precedes Google's own account chooser. */
(() => {
 const button=document.getElementById('googleLogin');
 const error=document.getElementById('loginError');
 const query=new URLSearchParams(location.search);
 const message=query.get('error')==='unavailable'
  ? 'Google sign-in is being configured. Please try again shortly.'
  : query.get('expired')==='1' ? 'Your session ended. Sign in again to continue.'
  : query.get('login_error')==='1'
  ? 'Sign-in was cancelled or could not be verified. Please try again.' : '';
 if(message){error.textContent=message;error.hidden=false;}
 button.addEventListener('click',event=>{
  if(button.getAttribute('aria-disabled')==='true'){event.preventDefault();return;}
  button.setAttribute('aria-disabled','true');
  button.querySelector('span').textContent='Connecting to Google...';
 });
 window.addEventListener('pageshow',()=>{
  button.removeAttribute('aria-disabled');
  button.querySelector('span').textContent='Continue with Google';
 });
 window.VelaurAccount.ready.then(()=>{
  if(window.VelaurAccount.profile){location.replace('/dashboard');return;}
  // Plan settings are authoritative; avoid promising a paused trial.
  return window.VelaurAccount.request('/api/public/plans').then(data=>{
   const box=document.querySelector('.login-trial');
   box.querySelector('strong').textContent=data.new_trials?data.trial_days+' days to find your flow.':'Your creative space awaits.';
   box.querySelector('p').textContent=data.new_trials
    ? 'Unlock your Creator trial after sign-in. '+data.trial_hours+' hours of exports. No card required.'
    : 'New trials are currently paused. Sign in to check your existing access.';
  });
 }).catch(()=>{});
})();
