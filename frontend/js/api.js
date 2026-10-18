const API_URL =
"https://nib-reader-api.onrender.com";
async function analyzeImage(imageData){

    const response =
        await fetch(
            API_URL + "/analyze",
            {
                method:"POST",

                headers:{
                    "Content-Type":"application/json"
                },

                body:JSON.stringify({
                    image:imageData
                })
            }
        );

    return await response.json();
}