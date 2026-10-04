import { test } from "node:test";
import assert from "node:assert/strict";
import { interact, runClefBrowser } from "../skills/ego-clef/scripts/browser.mjs";
import { decisionState, semanticActions, safeNavigation } from "../skills/ego-clef/scripts/semantic.mjs";

const url = 'https://catalog.example.test/';
const scope = u => u.origin === new URL(url).origin;
const values = { query: { value: 'local inference', hint: 'Search query' } };
const allowAction = action => ['fill', 'select', 'click', 'press'].includes(action.kind);
const answer = choice => ({ type: 'choice', choice, confidence: 0.95 });
function fakePage() {
  let query = '', category = 'all', applied = false;
  const calls = [];
  return { calls, url: async () => url, snapshot: async () => 'Search and category filters',
    waitForFunction: async () => {},
    evaluate: async () => ({ url, title: 'Catalog', text: applied ? 'Results: local inference tools' : 'Search catalog',
      controls: [
        {selector:'#query', tag:'input', role:'input', name:'Search query', type:'search', value:query},
        {selector:'#category', tag:'select', role:'select', name:'Category', value:category,
          options:[{label:'All',value:'all'},{label:'Tools',value:'tools'}]},
        {selector:'#apply', tag:'button', role:'button', name:'Apply filters'},
        {selector:'#delete', tag:'button', role:'button', name:'Delete all results'},
      ], scroll:{canDown:false} }),
    fill: async (selector, value) => { calls.push(['fill',selector,value]); query=value; },
    selectOption: async (selector, option) => { calls.push(['select',selector,option]); category=option.value; },
    click: async selector => { calls.push(['click',selector]); applied=true; },
    press: async (selector,key) => { calls.push(['press',selector,key]); applied=true; },
  };
}
const options = { goal:'Search local inference tools', mode:'interactive', values,
  allowNavigation:scope, allowAction, verify:state=>state.text.startsWith('Results:') };

test('generic semantic flow fills supplied value, selects option, clicks and independently verifies', async () => {
  const page = fakePage();
  const result = await runClefBrowser(page, {...options, decide:async(state, choices)=> {
    const next = !state.actions.find(a=>a.kind==='press') ? 'fill' : state.actions.find(a=>a.kind==='select')?.current_value === 'all' ? 'select' :
      state.text.startsWith('Results:') ? null : 'click';
    return answer(next ? choices[state.actions.find(a=>a.kind===next).id] : choices.at(-2));
  }});
  assert.equal(result.status, 'completed');
  assert.deepEqual(page.calls, [['fill','#query','local inference'],
    ['select','#category',{value:'tools'}], ['click','#apply']]);
  assert.equal(JSON.stringify(result.trace).includes('Search catalog'), false);
});

test('interactive shortcut works on an arbitrary origin and supports Enter search', async () => {
  const page = fakePage();
  const result = await interact(page, options.goal, {...options, configuration:async()=>({enabled:true}),
    decide:async(state, choices)=>answer(state.text.startsWith('Results:') ? choices.at(-2) :
      choices[state.actions.find(a=>a.kind===(state.actions.some(a=>a.kind==='press') ? 'press' : 'fill')).id]) });
  assert.equal(result.status,'completed');
  assert.deepEqual(page.calls.at(-1), ['press','#query','Enter']);
});

test('controls require agent policy; unknown values are never invented and risky controls are excluded', async () => {
  const state = await fakePage().evaluate();
  assert.deepEqual(semanticActions(state,values,scope),[]);
  const actions = semanticActions(state,{},scope,()=>true);
  assert.equal(actions.some(a=>a.kind==='fill'),false);
  assert.equal(actions.some(a=>a.name.includes('Delete')),false);
  assert.ok(semanticActions(state,values,scope,()=>true).some(a=>a.kind==='fill'));
});

test('changed target is rejected before any action', async () => {
  const page = fakePage(), observe = page.evaluate;
  let reads=0;
  page.evaluate=async()=>{const state=await observe(); if(++reads>1) state.controls[0].name='Different field'; return state;};
  const result=await runClefBrowser(page,{...options,decide:async (state, choices)=>answer(choices[state.actions.find(a=>a.kind==='fill').id])});
  assert.equal(result.reason,'stale_target');
  assert.deepEqual(page.calls,[]);
});

test('password or payment page hands off before a model call', async () => {
  const page=fakePage(), observe=page.evaluate;
  page.evaluate=async()=>({...await observe(),protectedPage:true});
  const result=await runClefBrowser(page,{...options,decide:async()=>assert.fail('No model call')});
  assert.equal(result.reason,'protected_page');
  assert.deepEqual(page.calls,[]);
});

test('popup or dialog returns control to the main agent', async () => {
  const page=fakePage();
  page.click=async()=>({popups:[{label:'p2'}]});
  const result=await runClefBrowser(page,{...options,decide:async (state, choices)=>answer(choices[state.actions.find(a=>a.kind==='click').id])});
  assert.equal(result.reason,'browser_interruption');
  assert.equal(result.trace.length,1);
});

test('unchanged control is not clicked repeatedly', async () => {
  const page=fakePage();
  page.click=async selector=>page.calls.push(['click',selector]);
  const result=await runClefBrowser(page,{...options,decide:async (state, choices)=>answer(choices[state.actions.find(a=>a.kind==='click').id])});
  assert.equal(result.reason,'no_progress');
  assert.equal(page.calls.length,1);
});

test('policy is reevaluated immediately before acting', async () => {
  const page=fakePage();
  let authorized=true;
  const result=await runClefBrowser(page,{...options,allowAction:()=>authorized,
    decide:async (state,choices)=>{authorized=false;return answer(choices[state.actions.find(a=>a.kind==='fill').id]);}});
  assert.equal(result.reason,'stale_target');
  assert.deepEqual(page.calls,[]);
});

test('scroll uses observed viewport coordinates and stops after verified evidence', async () => {
  const page=fakePage(), observe=page.evaluate;
  let scrolled=false;
  page.evaluate=async()=>({...await observe(),text:scrolled?'Results: found':'More below',
    scroll:{canDown:!scrolled,x:400,y:300,position:scrolled?600:0}});
  page.mouse={move:async(x,y)=>page.calls.push(['move',x,y]),
    wheel:async(x,y)=>{page.calls.push(['wheel',x,y]);scrolled=true;}};
  const result=await runClefBrowser(page,{...options,allowAction:()=>false,
    decide:async(state,choices)=>answer(state.actions.some(a=>a.kind==='scroll') ? choices[state.actions.find(a=>a.kind==='scroll').id] : choices.at(-2))});
  assert.equal(result.status,'completed');
  assert.deepEqual(page.calls,[['move',400,300],['wheel',0,600]]);
});

test('invalid supplied input fails before observation and unsafe navigation is excluded', async () => {
  await assert.rejects(runClefBrowser({}, {...options,values:{query:{value:42,hint:'query'}}}),TypeError);
  for(const target of ['javascript:alert(1)','https://u:p@catalog.example.test/',
    'https://catalog.example.test/%64elete','https://catalog.example.test/%XX',
    'https://catalog.example.test/?action=delete']) assert.equal(safeNavigation(new URL(target)),false);
});

test('decision context excludes unrelated controls and retains needed field state under action budget', async () => {
  const observation = await fakePage().evaluate();
  observation.controls.push({selector:'#unrelated',name:'Unrelated private content'.repeat(2000),options:Array(1000).fill('option')});
  const actions=semanticActions(observation,values,scope,allowAction);
  const state=decisionState(observation,actions,values);
  assert.equal(JSON.stringify(state).includes('Unrelated private'),false);
  assert.equal(state.actions.find(a=>a.kind==='fill').current_value,'');
  assert.ok(JSON.stringify(state).length<3000);
  const crowded={...observation,controls:Array.from({length:80},(_,i)=>({selector:'#item'+i,tag:'button',role:'button',name:'Item '+i})),
    scroll:{canDown:true}};
  const offered=semanticActions(crowded,{},scope,()=>true);
  assert.equal(offered.length,24);
  assert.equal(offered.at(-1).kind,'scroll');
});
