Curl for development
====================

During development, it can be useful to have the WiFi setup process listening for requests on your main network rather than starting its own access point.

In this state, you can use `curl` to experiment with the basic REST interface of the setup process.

Example requests
----------------

Set the address to use for all requests:

    $ ADDR=192.168.0.178

Request the root document:

    $ curl -v $ADDR

Or:

    $ curl -v $ADDR/index.html

Deliberately generate a 404 (Not Found):

    $ curl -v $ADDR/unknown

Set things up to make including the JSON accept header easier and make the same request with this header:

    $ JSON='Accept: application/json'
    $ curl -v -H "$JSON" $ADDR/unknown

The response body now comes back as JSON rather than HTML.

Some requests only return JSON:

    $ curl -v $ADDR/api/access-points

There's a slight pause for this request as it goes off and scans for access points.

If you've got `jq` installed try it again like so:

    $ curl -s -v $ADDR/api/access-points | jq .

Try the authentication endpoint:

    $ curl -v -H "$JSON" --data 'ssid=alpha&password=beta' $ADDR/api/access-point

Get it to fail by not providing an SSID:

    $ curl -v -H "$JSON" --data 'password=beta' $ADDR/api/access-point

Oddy `-v` doesn't show the data sent with `--data`, if you want to see what exactly is sent you need to use `--trace-ascii`:

    $ curl --trace-ascii - -H "$JSON" --data 'ssid=alpha&password=beta' $ADDR/api/access-point

The output isn't very readable - but everything is there.

Compression
-----------

One of the features I added to the web server used here is that if you request a file like `index.html` and there's no such file, it then checks for `index.html.gz`. If this file exists then the compressed file is served with the `Content-Encoding` header set to `gzip` to indicate this. This saves on storage space on the device and in transmission time to the client (which can typically handle the decompression step far faster than the board could).

Technically a server should only serve compressed content if the client used the `Accept-Encoding` to indicate that it can consume such content. However, in this setup this check isn't done and is simply assumed.

This is fine for normal browsers, which all accept compressed content, but if you request static content using `curl` you may be surprised when you get back binary content rather than the expected HTML, Javascript or whatever.

You can tell `curl` to advertise that it accepts compressed content and to handle the decompression with the `--compressed` flag:

    $ curl -v --compressed $ADDR/index.html

For more details see the Wikipedia [HTTP compression page](https://en.wikipedia.org/wiki/HTTP_compression).
