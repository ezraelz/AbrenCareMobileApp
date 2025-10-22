const tree = document.getElementById('tree');
const treeButton = document.getElementById('treeButton');

const collapse = () => {
   if (tree.style.display === 'none' && treeButton.textContent === 'Show tree') {
      tree.style.display = 'block';
      treeButton.textContent = 'Hide tree';
   } else {
      tree.style.display = 'none';
      treeButton.textContent = 'Show tree';
   }
}

treeButton.addEventListener('click', collapse);

const title = document.querySelector('h2').innerText;

const nav = document.querySelector('.nav');
console.log(nav)
const navHover = () => {
   if (window.innerHeight <= 60){
      nav.style.position = 'relative';
      
   } else {
      nav.style.position = 'sticky';
      nav.style.top = '0';
      nav.style.left = '0';
      nav.style.padding = '.5em';
   }
}
window.addEventListener('mouseout', navHover);
window.addEventListener('mouseover', navHover);

const conhid = document.querySelector('#hiddenConcepts');
const b1 = document.querySelector('#more');

const hiddenContent = () => {
   if (conhid.style.display === 'none') {
      conhid.style.display = 'block';
      b1.textContent = 'Less';
   } else {
      conhid.style.display = 'none';
      b1.textContent = 'More';
   }
}
b1.addEventListener('click', hiddenContent);

const conhid2 = document.querySelector('#hiddenDocuments');
const b2 = document.querySelector('#moreD');

const hiddenContent2 = () => {
   if (conhid2.style.display === 'none') {
      conhid2.style.display = 'block';
      b2.textContent = 'Less';
   } else {
      conhid2.style.display = 'none';
      b2.textContent = 'More';
   }
}
b2.addEventListener('click', hiddenContent2);

const s1 = document.querySelector('#s1');

const showS1Example = () => {
   document.querySelector('#s1 h3').textContent = 'Example';
   document.querySelector('#s1 p').textContent = 'const title = document.getElementById("main-title")';
}
s1.addEventListener('click', showS1Example);

const s2 = document.querySelector('#s2');

const showS2Example = () => {
   document.querySelector('#s2 h3').textContent = 'Example';
   document.querySelector('#s2 p').textContent = 'const texts = document.getElementsByClassName("text")';
}
s2.addEventListener('click', showS2Example);

const s3 = document.querySelector('#s3');

const showS3Example = () => {
   document.querySelector('#s3 h3').textContent = 'Example';
   document.querySelector('#s3 p').textContent = 'const divs = document.getElementsByTagName("div");';
}
s3.addEventListener('click', showS3Example);

const s4 = document.querySelector('#s4');

const showS4Example = () => {
   document.querySelector('#s4 h3').textContent = 'Example';
   document.querySelector('#s4 p').textContent = 'const firstBox = document.querySelector(".box");';
}
s4.addEventListener('click', showS4Example);

const s5 = document.querySelector('#s5');

const showS5Example = () => {
   document.querySelector('#s5 h3').textContent = 'Example';
   document.querySelector('#s5 p').textContent = 'const allBoxes = document.querySelectorAll(".box");';
}
s5.addEventListener('click', showS5Example);

const box = document.querySelector('.boxes');
const buttonCollapse = document.querySelector('#bC');

const boxCollapse = () => {
   if (box.style.height === '0em'){
      box.style.height = 'auto';
      buttonCollapse.textContent = 'v'
      box.style.overflow = 'hidden';
   } else {
      box.style.height = '0em';
      buttonCollapse.textContent = '^'
   }
}
buttonCollapse.addEventListener('click', boxCollapse);

// changing contents
const innerT = document.querySelector('#innerText');
const innerH = document.querySelector('#innerHTML');
const textC = document.querySelector('#textContent');

const handleHoverInnerT = ()=> {
      innerT.style.marginLeft = '4em';
}
const handleLeaveInnerT = () => {
  innerT.style.marginLeft = '0';
};

innerT.addEventListener('mouseover', handleHoverInnerT);
innerT.addEventListener('mouseout', handleLeaveInnerT);

