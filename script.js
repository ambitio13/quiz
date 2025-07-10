document.addEventListener("DOMContentLoaded", () => {
  const blocks = document.querySelectorAll(".block");
  const quizContainer = document.getElementById("quizContainer");
  const quizQuestion = document.getElementById("quizQuestion");
  const quizOptions = document.getElementById("quizOptions");
  const submitBtn = document.getElementById("submitBtn");
  const quizOuterBlock = document.querySelector(".quiz-outer-block");
  const formImage = document.getElementById("formImage"); // 获取表单上部图片元素
  const formTopImage = document.querySelector('.form-top-image'); // 获取表单上部图片容器元素
  const overlay = document.getElementById("overlay"); // 获取遮罩层元素

  // 初始隐藏外部背景块
  quizOuterBlock.style.display = "none";
  formImage.style.display = "none"; // 初始隐藏图片
  overlay.style.display = "none"; // 初始隐藏遮罩层

  // 定义每个方块的问题和选项，以及对应的图片
  const quizData = {
    block1: {
      question: "旅行者，你有什么想问的吗？",
      options: [
        "你知道世界上最长寿的树是什么树吗？它能活多少年呢？", 
        "为什么有些树冬天会掉叶子？而有的树不会呢？", 
        "如果森林里所有的树都不掉叶子，会发生什么？", 
        "冷知识：占位"
      ],
      image: "img/index01/block1.png" // 对应图片路径
    },
    block2: {
      question: "旅行者，你有什么想问的吗？",
      options: ["小溪里的鱼是会顺水流旅行，还是会一直待在同一个地方呢？", 
        "为什么冬天溪水结冰时鱼不会冻死？", 
        "如果一直不下雨，小溪的水快干了，小鱼们会怎么自救呢？", 
        "冷知识：占位"],
      image: "img/index01/block2.png"
    },
    block3: {
      question: "旅行者，你有什么想问的吗？",
      options: ["小溪边的石头主要有哪些颜色？他们分别都是什么石头呢？", 
        "为什么小溪转弯处会堆积更多石头？", 
        "如果小溪突然干涸，石头上的生物会怎么样？",
         "冷知识：占位"],
      image: "img/index01/block3.png"
    },
    block4: {
      question: "旅行者，你有什么想问的吗？",
      options: ["苔藓的颜色只有绿色吗？有没有黄色或褐色的？", 
        "苔藓一般长在石头的哪一面？原因是什么呢？",
         "如果人为地给苔藓施肥，它们会长得更快吗？",
        "冷知识：占位"],
      image: "img/index01/block4.png"
    },
    block5: {
      question: "旅行者，你有什么想问的吗？",
      options: ["小溪最终会流到哪里去？",
         "为什么森林里的小溪这么清澈？",
          "如果小溪里被引入外来侵略物种，会发生什么情况？",
           "冷知识：占位"],
      image: "img/index01/block5.png"
    }
  };

  // 鼠标移到图片上显示，点击后保持显示
  blocks.forEach((block) => {
    block.addEventListener("mouseover", () => {
      if (!block.dataset.submitted) {
        block.src = block.dataset.imgSrc;
        block.style.opacity = 1;
      }
    });

    block.addEventListener("mouseout", () => {
      if (!block.dataset.clicked && !block.dataset.submitted) {
        block.style.opacity = block.dataset.originalOpacity;
      }
    });

    block.addEventListener("click", () => {
      if (!block.dataset.submitted) {
        block.dataset.clicked = true;
        showQuiz(block);
        formTopImage.style.zIndex = 10; // 设置 z-index 为 10
      }
    });
  });

  // 点击选项框外面收起选项框
  document.addEventListener("click", (event) => {
    if (!quizContainer.contains(event.target) && !event.target.classList.contains("block")) {
      hideQuiz();
      formTopImage.style.zIndex = -1; // 恢复原来的 z-index
    }
  });

  // 更改提交按钮的内容
  submitBtn.textContent = "这是我好奇的问题";

  // 提交选项
  submitBtn.addEventListener("click", () => {
    const selectedOption = document.querySelector('input[name="option"]:checked');
    if (selectedOption) {
      const clickedBlockId = quizContainer.dataset.clickedBlock;
      const clickedBlock = document.getElementById(clickedBlockId);
      if (clickedBlock) {
        const data = {
          blockId: clickedBlockId,
          selectedOption: selectedOption.value
        };

        fetch('http://127.0.0.1:5000/submit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
          console.log("Backend response:", data.message);
          clickedBlock.dataset.submitted = true;
          clickedBlock.style.opacity = 1;
          clickedBlock.dataset.clicked = false;
          hideQuiz();
        })
        .catch(error => {
          console.error("Error:", error);
        });
      }
    } else {
      alert("Please select an option.");
    }
  });

  // 显示选项框
  function showQuiz(block) {
    const blockId = block.id;
    const quizInfo = quizData[blockId];
    
    // 设置问题和选项
    quizQuestion.textContent = quizInfo.question;
    quizOptions.innerHTML = "";

    quizInfo.options.forEach((option, index) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "option";
      input.value = option;
      label.appendChild(input);
      label.appendChild(document.createTextNode(option));
      quizOptions.appendChild(label);
      quizOptions.appendChild(document.createElement("br"));
    });

    // 设置对应的图片
    formImage.src = quizInfo.image;
    formImage.alt = `Image for ${blockId}`;
    formImage.style.display = "block"; // 显示图片

    // 显示表单和外部背景
    quizContainer.style.display = "flex";
    quizOuterBlock.style.display = "block";
    quizContainer.dataset.clickedBlock = blockId;

    // 显示遮罩层
    overlay.style.display = "block";
  }

  // 隐藏选项框
  function hideQuiz() {
    quizContainer.style.display = "none";
    quizOuterBlock.style.display = "none";
    formImage.style.display = "none"; // 隐藏图片
    const clickedBlockId = quizContainer.dataset.clickedBlock;
    const clickedBlock = document.getElementById(clickedBlockId);
    if (clickedBlock) {
      if (!clickedBlock.dataset.submitted) {
        clickedBlock.style.opacity = clickedBlock.dataset.originalOpacity;
        clickedBlock.dataset.clicked = false;
      }
    }
    formTopImage.style.zIndex = -1; // 恢复原来的 z-index

    // 隐藏遮罩层
    overlay.style.display = "none";
  }
});