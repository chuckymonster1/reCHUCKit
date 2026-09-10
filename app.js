const $=id=>document.getElementById(id);
const state={reference:null,stems:[],midi:[]};

function bindFile(id,key,nameId){
  $(id).addEventListener('change',e=>{
    const files=[...e.target.files];
    state[key]=e.target.multiple?files:files[0];
    $(nameId).textContent=files.length
      ?(e.target.multiple?`${files.length} loaded · ${files.map(f=>f.name).join(', ')}`:files[0].name)
      :(key==='reference'?'Nothing loaded':`No ${key} loaded`);
  });
}

bindFile('reference','reference','referenceName');
bindFile('stems','stems','stemName');
bindFile('midi','midi','midiName');
['humanize','timing','velocity'].forEach(id=>$(id).addEventListener('input',e=>$(id+'Value').textContent=e.target.value+'%'));

function card(title,value){return `<div class="status"><b>${title}</b><span>${value}</span></div>`}
function baseName(name){return name?name.replace(/\.[^.]+$/,''):'Untitled Record'}
function inputScore(){
  return Math.min(100,45+(state.reference?20:0)+Math.min(15,state.stems.length*3)+Math.min(20,state.midi.length*4));
}
function setBusy(isBusy){
  $('rebuild').disabled=isBusy;
  $('rebuild').classList.toggle('busy',isBusy);
  $('rebuild').innerHTML=isBusy?'<small>WORKING</small>reCHUCKing…':'<small>READY?</small>reCHUCKit';
}
function addFile(form,key,file){if(file)form.append(key,file,file.name)}

$('rebuild').addEventListener('click',async()=>{
  if(!state.reference&&!state.midi.length&&!state.stems.length){
    alert('Give reCHUCKit something to work with first — reference mix, stems, or MIDI.');
    return;
  }

  const form=new FormData();
  addFile(form,'reference',state.reference);
  state.stems.forEach(file=>addFile(form,'stems',file));
  state.midi.forEach(file=>addFile(form,'midi',file));
  form.append('humanize',Number($('humanize').value)/100);
  form.append('timing',Number($('timing').value)/100);
  form.append('velocity',Number($('velocity').value)/100);

  const session=baseName(state.reference?.name||state.midi[0]?.name||state.stems[0]?.name);
  $('sessionTitle').textContent=session;
  $('score').textContent=inputScore();
  $('statusGrid').innerHTML=card('ENGINE','Starting reconstruction…')+card('REFERENCE',state.reference?'Loaded':'Not supplied')+card('STEMS',`${state.stems.length} loaded`)+card('MIDI',`${state.midi.length} loaded`);
  $('enginePlan').textContent='Analyzing uploads and building the DAW-ready reconstruction package.';
  $('downloadBox').classList.add('hidden');
  $('report').classList.remove('hidden');
  $('report').scrollIntoView({behavior:'smooth',block:'start'});
  setBusy(true);

  try{
    const response=await fetch('/api/rebuild',{method:'POST',body:form});
    const payload=await response.json().catch(()=>({detail:'The server returned an unreadable response.'}));
    if(!response.ok)throw new Error(payload.detail||'reCHUCKit could not finish this session.');

    const analysis=payload.report?.analysis||{};
    const ref=analysis.reference;
    const midiReports=analysis.midi||[];
    const stemReports=analysis.stems||[];
    const totalNotes=midiReports.reduce((sum,item)=>sum+(item.cleaned?.notes||0),0);
    const bpm=ref?.tempo_bpm||midiReports[0]?.cleaned?.tempo_bpm||'—';

    $('statusGrid').innerHTML=
      card('ENGINE','Package ready')+
      card('TEMPO',bpm==='—'?'Not detected':`${bpm} BPM`)+
      card('STEMS',`${stemReports.length} analyzed`)+
      card('MIDI',`${midiReports.length} cleaned · ${totalNotes} notes`)+
      card('SAFETY','Original files untouched');

    $('enginePlan').textContent='Analysis complete. Timing and velocity cleanup were applied non-destructively to copied MIDI files. Pitch/note changes remain review-gated until their confidence checks are wired into automatic application.';
    $('downloadLink').href=payload.download_url;
    $('downloadLink').textContent='DOWNLOAD LOGIC / REASON PACKAGE';
    $('downloadBox').classList.remove('hidden');
  }catch(error){
    $('statusGrid').innerHTML=card('ENGINE','Stopped safely')+card('ERROR',error.message);
    $('enginePlan').textContent='No source file was overwritten. Fix the reported issue and run the session again.';
  }finally{
    setBusy(false);
  }
});
