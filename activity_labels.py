"""Readable phase/outcome descriptions. A server transfer is distinct from device saving."""
def phase(stage):
 text=str(stage or '').lower()
 if 'reading video' in text or 'information' in text:return 'video information'
 if 'verify duration' in text or 'verifying source' in text:return 'source duration verification'
 if 'checking actual' in text:return 'source duration check'
 if 'refreshing source' in text:return 'source access refresh'
 if 'download' in text:return 'source download'
 if 'merg' in text:return 'video/audio merge'
 if 'convert' in text:return 'media conversion'
 if 'prepar' in text:return 'preview preparation' if 'preview' in text else 'media preparation'
 return None

def describe(job):
 kind=job.get('kind');state=job.get('state');fmt=str(job.get('output_format') or '').upper()
 title='Preview' if kind=='preview' else (fmt if fmt in ('MP3','MP4') else 'Export')
 failed=phase(job.get('failed_stage'));inferred=False
 if state=='error' and not failed:
  error=str(job.get('error') or '').lower()
  if 'unable to download video data' in error:failed='source download';inferred=True
  elif 'media conversion failed' in error or 'ffmpeg processing failed' in error:failed='media conversion';inferred=True
 if state=='error':
  if kind=='export' and fmt=='MP3' and failed=='media conversion':failed='audio conversion'
  tone='error'
  if kind=='preview':label='Preview failed'
  elif failed in ('media conversion','audio conversion'):label=title+' conversion failed'
  else:label=title+' export failed'
  if failed:
   if not (kind=='export' and failed in ('media conversion','audio conversion')):label+=' - '+failed
   detail='Stopped during '+failed+'.'+(' This step is inferred from the stored error.' if inferred else '')
  else:detail='The job failed. The exact failing step was not recorded for this older entry.'
 elif state=='queued':label=title+' queued';tone='queued';detail='Waiting for a processing slot.'
 elif state=='running':
  label='Preparing preview' if kind=='preview' else title+' export in progress';tone='running';detail='Current step: '+(phase(job.get('stage')) or job.get('stage') or 'processing')+'.'
 elif state=='done':
  tone='done'
  if kind=='preview':label='Preview ready';detail='Video preview preparation finished successfully.'
  elif job.get('last_completed'):
   label=title+' file sent';detail='The server finished sending the full file. Saving it on the device is not confirmed.'
  elif job.get('last_download_request'):
   label=title+' download requested';detail='Export finished and the browser requested the file. A completed full-file transfer is not recorded yet.'
  elif job.get('file_ready'):
   label=title+' export completed â€” ready to download';detail='The '+title+' file was created successfully and is waiting to be downloaded.'
  else:label=title+' export completed â€” file unavailable';detail='Processing finished, but the stored export file is no longer available.'
 else:label=title+' status unavailable';tone='unknown';detail='No final processing result is recorded.'
 return dict(status_label=label,outcome_detail=detail,failure_phase=failed,failure_phase_inferred=inferred,job_type='Preview' if kind=='preview' else title+' export',status_tone=tone)
