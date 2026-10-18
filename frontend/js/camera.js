const video =
document.getElementById("video");

async function startCamera(){

    try{

        const stream =
            await navigator.mediaDevices.getUserMedia({

                video:{
                    facingMode:"environment"
                }

            });

        video.srcObject = stream;

    }

    catch(error){

        console.error(error);

    }

}

startCamera();