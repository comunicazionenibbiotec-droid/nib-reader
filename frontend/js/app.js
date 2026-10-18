const button =
document.getElementById("captureBtn");

button.addEventListener(
    "click",
    captureImage
);

async function captureImage(){

    const canvas =
        document.createElement("canvas");

    canvas.width =
        video.videoWidth;

    canvas.height =
        video.videoHeight;

    const ctx =
        canvas.getContext("2d");

    ctx.drawImage(
        video,
        0,
        0
    );

    const imageData =
        canvas.toDataURL(
            "image/jpeg",
            0.9
        );

    document
        .getElementById("preview")
        .src = imageData;

    const result =
        await analyzeImage(
            imageData
        );

    document
        .getElementById("result")
        .innerText =
        JSON.stringify(
            result,
            null,
            2
        );

}